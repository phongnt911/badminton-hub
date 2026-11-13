async page => {
  const probe=await page.context().newPage();
  try {
    await probe.goto('data:text/html,'+encodeURIComponent('<body><h1>WebGL diagnostic control</h1><canvas id="one" width="300" height="180"></canvas><canvas id="two" width="300" height="180"></canvas></body>'));
    const result=await probe.evaluate(()=>{
      const one=document.getElementById('one').getContext('webgl',{preserveDrawingBuffer:true});
      const two=document.getElementById('two').getContext('webgl2',{preserveDrawingBuffer:true});
      const p1=new Uint8Array(4),p2=new Uint8Array(4);
      if(one){one.clearColor(0,0.8,0,1);one.clear(one.COLOR_BUFFER_BIT);one.finish();one.readPixels(0,0,1,1,one.RGBA,one.UNSIGNED_BYTE,p1);}
      if(two){two.clearColor(0.7,0,0.8,1);two.clear(two.COLOR_BUFFER_BIT);two.finish();two.readPixels(0,0,1,1,two.RGBA,two.UNSIGNED_BYTE,p2);}
      return {webgl1:!!one,webgl2:!!two,lost1:one?one.isContextLost():null,lost2:two?two.isContextLost():null,pixel1:Array.from(p1),pixel2:Array.from(p2),error1:one?one.getError():null,error2:two?two.getError():null};
    });
    await probe.bringToFront();
    await probe.waitForTimeout(200);
    await probe.screenshot({path:'.build/web-matrix-capture/firefox-webgl-paint-control.png',scale:'css'});
    return {diagnosticOnly:true,...result};
  } finally {await probe.close();}
}
