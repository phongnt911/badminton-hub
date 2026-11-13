async page => {
  const probe=await page.context().newPage();
  try {
    await probe.goto('http://127.0.0.1:8088/#/sessions/10000000-0000-4000-8000-000000000099');
    await probe.locator('canvas').waitFor({state:'attached',timeout:15000});
    await probe.bringToFront();
    await probe.waitForTimeout(1000);
    await probe.screenshot({path:'.build/web-matrix-capture/firefox-flutter-before-semantics.png',scale:'css'});
    const placeholder=probe.locator('flt-semantics-placeholder');
    if(await placeholder.count())await placeholder.evaluate(el=>el.click());
    await probe.getByRole('heading',{name:'Chi tiết buổi chơi',exact:true}).waitFor({timeout:10000});
    await probe.screenshot({path:'.build/web-matrix-capture/firefox-flutter-after-semantics.png',scale:'css'});
    return {diagnosticOnly:true,flutterCanvasAttached:true,semanticHeadingPresent:true,viewport:probe.viewportSize()};
  } finally {await probe.close();}
}
