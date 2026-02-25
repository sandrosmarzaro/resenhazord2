import { MongoClient } from 'mongodb';

const MONGODB_URI = process.env.MONGODB_URI;
const DB_NAME = 'resenhazord2';
const COLLECTION_NAME = 'auth_state';

function getClient(): MongoClient {
  if (!MONGODB_URI) {
    console.error('❌ MONGODB_URI environment variable is not set');
    process.exit(1);
  }
  return new MongoClient(MONGODB_URI);
}

async function checkAuthSession(): Promise<void> {
  console.log('🔍 Checking MongoDB auth session...');

  const client = getClient();
  try {
    await client.connect();
    const collection = client.db(DB_NAME).collection(COLLECTION_NAME);

    const total = await collection.countDocuments();
    console.log(`✅ Found ${total} document(s) in ${DB_NAME}.${COLLECTION_NAME}`);

    const creds = await collection.findOne({ _id: 'creds' as unknown as import('mongodb').ObjectId });
    if (creds) {
      console.log('   - creds: present');
    } else {
      console.log('⚠️  Missing required document: creds');
      console.log('Session may be corrupted or not initialized yet');
    }
  } catch (error) {
    console.error('❌ Error connecting to MongoDB:', (error as Error).message);
  } finally {
    await client.close();
  }
}

async function cleanSession(): Promise<void> {
  console.log('\n🧹 Cleaning MongoDB auth session...');

  const client = getClient();
  try {
    await client.connect();
    const collection = client.db(DB_NAME).collection(COLLECTION_NAME);

    const result = await collection.deleteMany({});
    console.log(`✅ Deleted ${result.deletedCount} document(s) from ${DB_NAME}.${COLLECTION_NAME}`);
    console.log('ℹ️  Please restart the app and scan QR code again');
  } catch (error) {
    console.error('❌ Error cleaning MongoDB session:', (error as Error).message);
  } finally {
    await client.close();
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
  console.log('   - Make sure MONGODB_URI is set in your environment');
  console.log('   - Make sure you have a stable internet connection');
  console.log('   - Check if WhatsApp Web is not open elsewhere');
  console.log('   - Try using a different phone number if issue persists');
}
