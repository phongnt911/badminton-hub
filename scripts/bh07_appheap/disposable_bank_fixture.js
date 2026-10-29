// Production disposable club & bank fixture helper for BH-07 V2b heap verification.
// Enforces isolated, run-only club and bank fixtures with strict ownership, preflight collision
// refusal, exact POST reconciliation against schema, child-first cleanup, and verified absence.

const crypto = require('node:crypto');

const sha12 = (val) => crypto.createHash('sha256').update(String(val || '')).digest('hex').slice(0, 12);

function assertLocalEndpoint(url) {
  const host = ((/^https?:\/\/(\[[^\]]+\]|[^/:?#]+)/i.exec(String(url || '')) || [])[1] || '').toLowerCase();
  if (!['127.0.0.1', 'localhost', '::1', '[::1]'].includes(host)) {
    throw new Error(`refusing to write run-only fixture to non-local endpoint (${url || 'no URL'})`);
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
  return /duplicate|constraint|conflict|permission|forbidden|unauthorized|PGRST/i.test(err.message || '');
}

class DisposableBankFixture {
  constructor(options = {}) {
    this.clubId = options.clubId || crypto.randomUUID();
    const nonce = options.nonce || crypto.randomBytes(4).toString('hex');
    this.clubName = options.clubName || `BH07 Bank Test Club ${nonce}`;
    this.memberId = options.memberId || crypto.randomUUID();
    this.bankId = options.bankId || crypto.randomUUID();
    this.bankCode = options.bankCode || 'VCB';
    // 16-digit account number, distinctly starts with 99990000 to prevent UUID substring coincidence
    this.accountNumber = options.accountNumber || ('99990000' + Math.floor(10000000 + Math.random() * 90000000).toString());
    this.accountName = options.accountName || `CHU TAI KHOAN ${nonce.toUpperCase()}`;
    this.ownerUserId = options.ownerUserId || null;

    // Operation tracking
    this.createdClub = false;
    this.createdMember = false;
    this.createdBank = false;
    this.clubRemoved = false;
    this.bankRemoved = false;
    this.clubVerifiedAbsent = false;
    this.bankVerifiedAbsent = false;
    this.refused = null;
    this.error = null;
  }

  get created() {
    return this.createdClub || this.createdMember || this.createdBank;
  }

  // Anchor to real authenticated owner of CLUB_A, never guessed from roster
  async resolveOwnerAnchor(transport, clubAId = 'aaaaaaaa-1111-4111-8111-111111111111') {
    const rows = await transport.restGet(`clubs?id=eq.${clubAId}&select=owner_user_id`);
    if (!rows || !rows.length || !rows[0].owner_user_id) {
      throw new Error(`cannot resolve owner anchor from club ${clubAId}`);
    }
    this.ownerUserId = rows[0].owner_user_id;
    return this.ownerUserId;
  }

  async ensure(transport) {
    if (transport.apiUrl) {
      assertLocalEndpoint(transport.apiUrl);
    }
    if (!this.ownerUserId) {
      await this.resolveOwnerAnchor(transport);
    }

    // 1. Preflight collisions on prospective IDs
    const preClub = await transport.restGet(`clubs?id=eq.${this.clubId}&select=id`);
    if (preClub && preClub.length) {
      this.refused = 'preexisting_club_id_exists';
      throw new Error(`preflight collision: club ${this.clubId} already exists`);
    }

    const preMember = await transport.restGet(`club_members?id=eq.${this.memberId}&select=id`);
    if (preMember && preMember.length) {
      this.refused = 'preexisting_member_id_exists';
      throw new Error(`preflight collision: member ${this.memberId} already exists`);
    }

    const preBank = await transport.restGet(`club_bank_accounts?id=eq.${this.bankId}&select=id`);
    if (preBank && preBank.length) {
      this.refused = 'preexisting_bank_id_exists';
      throw new Error(`preflight collision: bank account ${this.bankId} already exists`);
    }

    // 2. Create Club with exact schema (owner_user_id, NOT created_by)
    try {
      await transport.restWrite('POST', 'clubs', [{
        id: this.clubId,
        owner_user_id: this.ownerUserId,
        name: this.clubName,
        status: 'active',
        visibility: 'private',
      }]);
      this.createdClub = true;
    } catch (err) {
      const status = extractHttpStatus(err);
      if (status && !err.status) err.status = status;
      if (isDefiniteRejectError(err)) {
        this.refused = `club_post_rejected_${status || 400}`;
        this.createdClub = false;
        throw err;
      }
      // Ambiguous timeout/drop: readback and strictly verify ownership markers
      const left = await transport.restGet(`clubs?id=eq.${this.clubId}&select=id,owner_user_id,name`);
      if (left && left.length === 1 && left[0].id === this.clubId
          && left[0].owner_user_id === this.ownerUserId && left[0].name === this.clubName) {
        this.createdClub = true;
      } else {
        this.createdClub = false;
      }
      this.error = err.message;
      throw err;
    }

    // 3. Create Club Member (owner role, display_name required)
    try {
      await transport.restWrite('POST', 'club_members', [{
        id: this.memberId,
        club_id: this.clubId,
        user_id: this.ownerUserId,
        display_name: 'Club Owner',
        role: 'owner',
        status: 'active',
      }]);
      this.createdMember = true;
    } catch (err) {
      const status = extractHttpStatus(err);
      if (status && !err.status) err.status = status;
      if (isDefiniteRejectError(err)) {
        this.refused = `member_post_rejected_${status || 400}`;
        this.createdMember = false;
        throw err;
      }
      const left = await transport.restGet(`club_members?id=eq.${this.memberId}&select=id,club_id,user_id,role`);
      if (left && left.length === 1 && left[0].id === this.memberId
          && left[0].club_id === this.clubId && left[0].user_id === this.ownerUserId && left[0].role === 'owner') {
        this.createdMember = true;
      } else {
        this.createdMember = false;
      }
      this.error = err.message;
      throw err;
    }

    // 4. Create Club Bank Account (exact schema: no user_id column)
    try {
      await transport.restWrite('POST', 'club_bank_accounts', [{
        id: this.bankId,
        club_id: this.clubId,
        bank_code: this.bankCode,
        account_number: this.accountNumber,
        account_name: this.accountName,
        status: 'active',
      }]);
      this.createdBank = true;
    } catch (err) {
      const status = extractHttpStatus(err);
      if (status && !err.status) err.status = status;
      if (isDefiniteRejectError(err)) {
        this.refused = `bank_post_rejected_${status || 400}`;
        this.createdBank = false;
        throw err;
      }
      const left = await transport.restGet(`club_bank_accounts?id=eq.${this.bankId}&select=id,club_id,account_number,account_name`);
      if (left && left.length === 1 && left[0].id === this.bankId
          && left[0].club_id === this.clubId && left[0].account_number === this.accountNumber
          && left[0].account_name === this.accountName) {
        this.createdBank = true;
      } else {
        this.createdBank = false;
      }
      this.error = err.message;
      throw err;
    }

    return this;
  }

  async cleanup(transport) {
    const errors = [];

    // Child-first order:
    // 1. Bank account
    if (this.createdBank) {
      try {
        await transport.restWrite('DELETE', `club_bank_accounts?id=eq.${this.bankId}`);
        this.bankRemoved = true;
      } catch (err) {
        errors.push(`delete_bank: ${err.message}`);
      }
      try {
        const left = await transport.restGet(`club_bank_accounts?id=eq.${this.bankId}&select=id`);
        this.bankVerifiedAbsent = Array.isArray(left) && left.length === 0;
      } catch (err) {
        this.bankVerifiedAbsent = false;
        errors.push(`verify_bank_absent: ${err.message}`);
      }
    } else {
      // If we never created it, verify absence
      try {
        const left = await transport.restGet(`club_bank_accounts?id=eq.${this.bankId}&select=id`);
        this.bankVerifiedAbsent = Array.isArray(left) && left.length === 0;
      } catch (err) {
        this.bankVerifiedAbsent = false;
      }
    }

    // 2. Member
    if (this.createdMember) {
      try {
        await transport.restWrite('DELETE', `club_members?id=eq.${this.memberId}`);
      } catch (err) {
        errors.push(`delete_member: ${err.message}`);
      }
    }

    // 3. Club
    if (this.createdClub) {
      try {
        await transport.restWrite('DELETE', `clubs?id=eq.${this.clubId}`);
        this.clubRemoved = true;
      } catch (err) {
        errors.push(`delete_club: ${err.message}`);
      }
      try {
        const left = await transport.restGet(`clubs?id=eq.${this.clubId}&select=id`);
        this.clubVerifiedAbsent = Array.isArray(left) && left.length === 0;
      } catch (err) {
        this.clubVerifiedAbsent = false;
        errors.push(`verify_club_absent: ${err.message}`);
      }
    } else {
      try {
        const left = await transport.restGet(`clubs?id=eq.${this.clubId}&select=id`);
        this.clubVerifiedAbsent = Array.isArray(left) && left.length === 0;
      } catch (err) {
        this.clubVerifiedAbsent = false;
      }
    }

    if (errors.length) {
      this.error = errors.join('; ');
    }

    return this.getReceipt();
  }

  getReceipt() {
    return {
      disposable_club_id_sha256_12: sha12(this.clubId),
      disposable_bank_id_sha256_12: sha12(this.bankId),
      disposable_club_created: this.createdClub === true,
      disposable_bank_created: this.createdBank === true,
      disposable_club_removed: this.clubRemoved === true,
      disposable_bank_removed: this.bankRemoved === true,
      disposable_club_verified_absent: this.clubVerifiedAbsent === true,
      disposable_bank_verified_absent: this.bankVerifiedAbsent === true,
      created: this.created,
      removed: (this.createdBank ? this.bankRemoved : true) && (this.createdClub ? this.clubRemoved : true),
      verified_absent: this.bankVerifiedAbsent === true && this.clubVerifiedAbsent === true,
      refused: this.refused,
      error: this.error,
    };
  }
}

// Scenario driver for fake-fetch testing (BKR6)
async function runFixtureScenario(scenario, mockTransport) {
  const fixture = new DisposableBankFixture(mockTransport.fixtureOptions || {});
  let ensureError = null;
  try {
    await fixture.ensure(mockTransport);
  } catch (err) {
    ensureError = err.message;
  }
  const cleanupReceipt = await fixture.cleanup(mockTransport);
  return {
    scenario,
    ensureError,
    created: fixture.created,
    createdClub: fixture.createdClub,
    createdBank: fixture.createdBank,
    refused: fixture.refused,
    cleanupReceipt,
    calls: mockTransport.calls || [],
  };
}

module.exports = {
  DisposableBankFixture,
  assertLocalEndpoint,
  runFixtureScenario,
  sha12,
};

if (require.main === module) {
  const args = process.argv.slice(2);
  const scenario = args[0] || 'test';
  console.log(JSON.stringify({ status: 'ok', scenario, module: 'disposable_bank_fixture' }));
}
