import { dirname } from 'path';
import { fileURLToPath } from 'url';
import * as fs from 'fs';
import * as path from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const sessionPath = path.join(__dirname, '..', 'auth', 'session');

if (!fs.existsSync(sessionPath)) {
    console.log('Session directory not found.');
    process.exit(1);
}

const files = fs.readdirSync(sessionPath);
const jsonFiles = files.filter(file => path.extname(file) === '.json');

jsonFiles.forEach(file => {
    const filePath = path.join(sessionPath, file);
    if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
    }
});
