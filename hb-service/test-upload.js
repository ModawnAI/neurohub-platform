import fs from 'fs';
import path from 'path';
import FormData from 'form-data';

async function testUpload() {
  const form = new FormData();

  // Add files
  form.append('spo2', fs.createReadStream('/Users/hjpark/Library/CloudStorage/Dropbox/develop/nodes/hypoxicburden-service/tmp/AllTrends_OSat.csv'));
  form.append('eventlist', fs.createReadStream('/Users/hjpark/Library/CloudStorage/Dropbox/develop/nodes/hypoxicburden-service/tmp/sample001_eventlist.txt'));
  form.append('hypn', fs.createReadStream('/Users/hjpark/Library/CloudStorage/Dropbox/develop/nodes/hypoxicburden-service/tmp/AllTrends_Hypnogram.csv'));

  try {
    const response = await fetch('http://localhost:3000/api/hb', {
      method: 'POST',
      body: form
    });

    const result = await response.json();
    console.log('Upload successful!');
    console.log('Response:', JSON.stringify(result, null, 2));
  } catch (error) {
    console.error('Upload failed:', error.message);
  }
}

testUpload();