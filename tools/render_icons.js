// Renderiza docs/brand/icons/*.svg a src/assets/icons/<nombre>.png (activo) y <nombre>_off.png (inactivo).
const {chromium} = require('playwright');
const fs = require('fs'), path = require('path');
const SRC = 'docs/brand/icons', OUT = 'src/assets/icons';
const VARIANTS = {'': ['#F5F5F5', '#E5194B'], '_off': ['#8A8A8A', '#7A1229']};
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({viewport: {width: 144, height: 144}});
  for (const f of fs.readdirSync(SRC).filter(f => f.endsWith('.svg'))) {
    const svg = fs.readFileSync(path.join(SRC, f), 'utf8');
    for (const [suffix, [line, dot]] of Object.entries(VARIANTS)) {
      const s = svg.replaceAll('LINE', line).replaceAll('DOT', dot).replace('<svg ', '<svg width="144" height="144" ');
      await p.setContent(`<html><body style="margin:0;background:transparent">${s}</body></html>`);
      await p.screenshot({path: path.join(OUT, f.replace('.svg', suffix + '.png')), omitBackground: true, clip: {x: 0, y: 0, width: 144, height: 144}});
    }
  }
  await b.close();
})();
