// Production disposable club ledger fixture helper for BH-07 V2b heap verification.
// Enforces isolated, run-only ledger fixtures with strict ownership, preflight collision
// refusal, exact POST reconciliation against schema, child-first cleanup, and verified absence.

const crypto = require('node:crypto');

const sha12 = (val) => crypto.createHash('sha256').update(String(val || '')).digest('hex').slice(0, 12);

function assertLocalEndpoint(url) {
  if (!url || typeof url !== 'string') {
    throw new Error('refusing to operate without an explicit local API URL');
  }
  const host = ((/^https?:\/\/(\[[^\]]+\]|[^/:?#]+)/i.exec(url) || [])[1] || '').toLowerCase();
  if (!['127.0.0.1', 'localhost', '::1', '[::1]'].includes(host)) {
    throw new Error(`refusing to write run-only fixture to non-local endpoint (${url})`);
  }
}

function extractHttpStatus(err) {
  if (!err) return null;
  if (typeof err.status === 'number' && Number.isInteger(err.status)) return err.status;
  const m = String(err.message || '').match(/PostgREST\s+(?:POST|GET|DELETE)\s+\S+:\s+(\d{3})/i);
  if (m) return parseInt(m[1], 10);
  return null;
}

function isDefiniteRejectError(err) {
  const status = extractHttpStatus(err);
  if (status !== null && status >= 400 && status < 500) return true;
  return /duplicate|constraint|conflict|permission|forbidden|unauthorized|PGRST/i.test(err && err.message || '');
}

class DisposableLedgerFixture {
  constructor(options = {}) {
    this.clubId = options.clubId || null;
    this.ownerUserId = options.ownerUserId || null;
    this.transactionId = options.transactionId || crypto.randomUUID();
    const nonce = options.nonce || crypto.randomBytes(4).toString('hex');
    this.title = options.title || `BH07 Ledger Test Thu Quy ${nonce}`;
    this.amountVnd = typeof options.amountVnd === 'number' ? options.amountVnd : 50000;
    this.direction = options.direction || 'income';
    this.sourceType = options.sourceType || 'manual';

    // Operation tracking
    this.createdLedger = false;
    this.ledgerRemoved = false;
    this.ledgerVerifiedAbsent = false;
    this.refused = null;
    this.error = null;
  }

  get created() {
    return this.createdLedger === true;
  }

  async ensure(transport) {
    assertLocalEndpoint(transport && transport.apiUrl);
    if (!this.clubId || !this.ownerUserId) {
      throw new Error('DisposableLedgerFixture requires owned parent clubId and ownerUserId');
    }

    // 1. Preflight collision refusal on prospective transaction ID
    const pre = await transport.restGet(`club_transactions?id=eq.${this.transactionId}&select=id`);
    if (pre && pre.length) {
      this.refused = 'preexisting_ledger_id_exists';
      throw new Error(`preflight collision: ledger transaction ${this.transactionId} already exists`);
    }

    // 2. Insert transaction with exact allowed schema
    const payload = [{
      id: this.transactionId,
      club_id: this.clubId,
      direction: this.direction,
      amount_vnd: this.amountVnd,
      title: this.title,
      source_type: this.sourceType,
      created_by: this.ownerUserId,
    }];

    try {
      await transport.restWrite('POST', 'club_transactions', payload);
    } catch (err) {
      const status = extractHttpStatus(err);
      if (status && !err.status) err.status = status;
      if (isDefiniteRejectError(err)) {
        this.refused = `ledger_post_rejected_${status || 400}`;
        this.createdLedger = false;
        throw err;
      }
      // Ambiguous timeout/network drop: readback and strictly verify ownership markers
      try {
        const left = await transport.restGet(
          `club_transactions?id=eq.${this.transactionId}&select=id,club_id,direction,amount_vnd,title,source_type,created_by`
        );
        if (left && left.length === 1 && left[0].id === this.transactionId
            && left[0].club_id === this.clubId && left[0].created_by === this.ownerUserId
            && left[0].amount_vnd === this.amountVnd && left[0].title === this.title
            && left[0].source_type === this.sourceType && left[0].direction === this.direction) {
          this.createdLedger = true;
        } else {
          this.createdLedger = false;
        }
      } catch (readbackErr) {
        this.createdLedger = false;
        this.error = `ambiguous_post_readback_failed: ${readbackErr.message}`;
      }
      this.error = this.error || err.message;
      throw err;
    }

    // 3. Exact full-row readback after successful POST ack before assuming ownership
    try {
      const readback = await transport.restGet(
        `club_transactions?id=eq.${this.transactionId}&select=id,club_id,direction,amount_vnd,title,source_type,created_by`
      );
      if (!readback || readback.length !== 1 || readback[0].id !== this.transactionId
          || readback[0].club_id !== this.clubId || readback[0].created_by !== this.ownerUserId
          || readback[0].amount_vnd !== this.amountVnd || readback[0].title !== this.title
          || readback[0].source_type !== this.sourceType || readback[0].direction !== this.direction) {
        this.createdLedger = false;
        this.error = 'post_ack_but_readback_missing_or_mismatch';
        throw new Error(`successful POST but exact readback failed for ledger transaction ${this.transactionId}`);
      }
      this.createdLedger = true;
    } catch (readbackErr) {
      this.createdLedger = false;
      this.error = this.error || readbackErr.message;
      throw readbackErr;
    }

    return this;
  }

  async cleanup(transport) {
    assertLocalEndpoint(transport && transport.apiUrl);
    const errors = [];
    if (this.createdLedger) {
      try {
        await transport.restWrite('DELETE', `club_transactions?id=eq.${this.transactionId}`);
        this.ledgerRemoved = true;
      } catch (err) {
        errors.push(`delete_ledger: ${err.message}`);
      }
      try {
        const left = await transport.restGet(`club_transactions?id=eq.${this.transactionId}&select=id`);
        this.ledgerVerifiedAbsent = Array.isArray(left) && left.length === 0;
        if (!this.ledgerVerifiedAbsent) {
          errors.push('delete_ledger_noop: row still exists after delete');
        }
      } catch (err) {
        this.ledgerVerifiedAbsent = false;
        errors.push(`verify_ledger_absent: ${err.message}`);
      }
    } else {
      // If we never created the row (e.g. refused or 403 or mismatch), never DELETE! Only verify absence.
      try {
        const left = await transport.restGet(`club_transactions?id=eq.${this.transactionId}&select=id`);
        this.ledgerVerifiedAbsent = Array.isArray(left) && left.length === 0;
      } catch (err) {
        this.ledgerVerifiedAbsent = false;
      }
    }

    if (errors.length) {
      this.error = errors.join('; ');
    }

    return this.getReceipt();
  }

  getReceipt() {
    const receipt = {
      disposable_ledger_id_sha256_12: sha12(this.transactionId),
      disposable_ledger_created: this.createdLedger === true,
      disposable_ledger_removed: this.ledgerRemoved === true,
      disposable_ledger_verified_absent: this.ledgerVerifiedAbsent === true,
      created: this.createdLedger === true,
      removed: this.createdLedger ? this.ledgerRemoved === true : true,
      verified_absent: this.ledgerVerifiedAbsent === true,
      refused: this.refused,
      error: this.error,
    };
    if (this.error) {
      receipt.disposable_ledger_error = this.error;
    }
    return receipt;
  }
}

module.exports = {
  DisposableLedgerFixture,
  assertLocalEndpoint,
  extractHttpStatus,
  isDefiniteRejectError,
  sha12,
};
