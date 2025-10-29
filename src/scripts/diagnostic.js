import { readdir, rm } from 'fs/promises';
import { join } from 'path';
import { existsSync } from 'fs';

async function checkAuthSession() {
    const sessionPath = join(process.cwd(), 'auth_session');

    console.log('🔍 Checking auth session...');
    console.log(`Session path: ${sessionPath}`);

    if (!existsSync(sessionPath)) {
        console.log('❌ No auth_session folder found');
        return;
    }

    try {
        const files = await readdir(sessionPath);
        console.log(`✅ Found ${files.length} files in session:`);
        files.forEach(file => console.log(`   - ${file}`));

        const requiredFiles = ['creds.json'];
        const missingFiles = requiredFiles.filter(f => !files.includes(f));

        if (missingFiles.length > 0) {
            console.log(`⚠️  Missing required files: ${missingFiles.join(', ')}`);
            console.log('Session may be corrupted');
        }

    } catch (error) {
        console.error('❌ Error reading session:', error.message);
    }
}

async function cleanSession() {
    const sessionPath = join(process.cwd(), 'auth_session');

    console.log('\n🧹 Cleaning auth session...');

    try {
        await rm(sessionPath, { recursive: true, force: true });
        console.log('✅ Session cleaned successfully');
        console.log('ℹ️  Please restart the app and scan QR code again');
    } catch (error) {
        console.error('❌ Error cleaning session:', error.message);
    }
}

console.log('=== WhatsApp Connection Diagnostic ===\n');

const args = process.argv.slice(2);

if (args.includes('--clean')) {
    await cleanSession();
} else {
    await checkAuthSession();
    console.log('\n💡 Tips:');
    console.log('   - If session is corrupted, run: node diagnostic.js --clean');
    console.log('   - Make sure you have a stable internet connection');
    console.log('   - Check if WhatsApp Web is not open elsewhere');
    console.log('   - Try using a different phone number if issue persists');
}