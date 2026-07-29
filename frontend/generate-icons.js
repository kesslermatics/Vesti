import sharp from 'sharp';
import { readFileSync } from 'fs';

const svg = readFileSync('./public/favicon.svg');

async function generateIcons() {
  // Generate 192x192 icon
  await sharp(svg)
    .resize(192, 192)
    .png()
    .toFile('./public/icon-192.png');
  
  console.log('✓ Generated icon-192.png');

  // Generate 512x512 icon
  await sharp(svg)
    .resize(512, 512)
    .png()
    .toFile('./public/icon-512.png');
  
  console.log('✓ Generated icon-512.png');

  // Generate apple-touch-icon (180x180 is standard)
  await sharp(svg)
    .resize(180, 180)
    .png()
    .toFile('./public/apple-touch-icon.png');
  
  console.log('✓ Generated apple-touch-icon.png');
}

generateIcons().catch(console.error);
