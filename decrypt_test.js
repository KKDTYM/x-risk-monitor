const fs = require('fs');
const crypto = require('crypto');

async function testDecrypt() {
  try {
    const credPath = 'C:/Users/Administrator/.workbuddy/connectors/1cd60f3d-1c27-48da-a9da-5fe47ae3de64/.credentials.v3.json';
    if (!fs.existsSync(credPath)) {
      console.log("Credentials file not found");
      return;
    }
    const cred = JSON.parse(fs.readFileSync(credPath, 'utf8'));
    const enc = cred.encryption;
    const salt = Buffer.from(enc.salt, 'base64');
    const keyCheck = Buffer.from(enc.keyCheck, 'base64');
    
    // 候选主密钥
    const candidates = ['workbuddy', 'codebuddy', 'workbuddy_master', 'codebuddy_master', ''];
    
    for (const masterKey of candidates) {
      // 1. pbkdf2
      try {
        const derivedKey = crypto.pbkdf2Sync(masterKey, salt, 10000, 32, 'sha256');
        const kc = crypto.createHmac('sha256', derivedKey).update('keycheck').digest();
        if (kc.slice(0, 16).equals(keyCheck.slice(0, 16))) {
          console.log("PBKDF2 Match:", masterKey);
          return { key: derivedKey, masterKey };
        }
      } catch(e) {}
      
      // 2. scrypt
      try {
        const derivedKey = crypto.scryptSync(masterKey, salt, 32, { N: 16384, r: 8, p: 1 });
        const kc = crypto.createHmac('sha256', derivedKey).update('keycheck').digest();
        if (kc.slice(0, 16).equals(keyCheck.slice(0, 16))) {
          console.log("scrypt Match:", masterKey);
          return { key: derivedKey, masterKey };
        }
      } catch(e) {}

      // 3. hkdf
      try {
        // node crypto.hkdf
        const derivedKey = await new Promise((resolve) => {
          crypto.hkdf('sha256', masterKey, salt, 'keycheck', 32, (err, derivedKey) => {
            resolve(derivedKey);
          });
        });
        if (derivedKey) {
          const kc = crypto.createHmac('sha256', derivedKey).update('keycheck').digest();
          if (kc.slice(0, 16).equals(keyCheck.slice(0, 16))) {
            console.log("HKDF Match:", masterKey);
            return { key: derivedKey, masterKey };
          }
        }
      } catch(e) {}
    }
    console.log("No master key matched.");
  } catch (err) {
    console.error("Test error:", err);
  }
}

testDecrypt();
