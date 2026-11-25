// Renderiza docs/brand/intro.svg cuadro a cuadro: node tools/render_intro.js <outdir> <segundos> <escala>
const {chromium} = require('playwright');
const [out, secs, scale] = [process.argv[2], +process.argv[3], +process.argv[4] || 1];
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({viewport: {width: 486, height: 454}, deviceScaleFactor: scale});
  await p.goto('file://' + process.cwd() + '/docs/brand/intro.svg');
  await p.evaluate(() => { document.documentElement.pauseAnimations(); document.getAnimations().forEach(a => a.pause()); });
  const fps = 25;
  for (let i = 0; i < Math.round(secs * fps); i++) {
    const t = i / fps;
    await p.evaluate(t => { document.documentElement.setCurrentTime(t); document.getAnimations().forEach(a => a.currentTime = t * 1000); }, t);
    await p.screenshot({path: `${out}/f${String(i).padStart(3, '0')}.png`});
  }
  await b.close();
})();
