import { computeHypoxicBurdenFromFiles } from './hb-calculator.js';

async function test() {
  try {
    const result = await computeHypoxicBurdenFromFiles(
      '../tmp/AllTrends_OSat.csv',
      '../tmp/sample001_eventlist.txt', 
      '../tmp/AllTrends_Hypnogram.csv'
    );
    
    console.log('Result keys:', Object.keys(result));
    console.log('Has avg:', !!result.avg);
    console.log('Has filt:', !!result.filt);
    console.log('avg length:', result.avg?.length);
    console.log('filt length:', result.filt?.length);
    console.log('First few avg:', result.avg?.slice(0, 3));
    console.log('First few filt:', result.filt?.slice(0, 3));
    
    // Generate HTML
    const htmlContent = generateHTMLReport(result);
    console.log('HTML generated, length:', htmlContent.length);
    
    // Check if avg and filt are in HTML
    const hasAvg = htmlContent.includes('"avg":');
    const hasFilt = htmlContent.includes('"filt":');
    console.log('HTML contains avg:', hasAvg);
    console.log('HTML contains filt:', hasFilt);
    
  } catch (error) {
    console.error('Error:', error);
  }
}

function generateHTMLReport(data) {
  return `<!DOCTYPE html>
<html>
<body>
<script>
const resultData = ${JSON.stringify(data)};
console.log('Embedded data has avg:', !!resultData.avg);
console.log('Embedded data has filt:', !!resultData.filt);
console.log('avg length:', resultData.avg?.length);
console.log('filt length:', resultData.filt?.length);
</script>
</body>
</html>`;
}

test();
