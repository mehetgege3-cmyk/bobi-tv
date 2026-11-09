#!/usr/bin/env node
/**
 * Cookie JSON'ından access_token'ı doğrudan çıkarır.
 * buildCleanArenaCookie'yi bypass eder.
 */
import { readFileSync } from 'fs';

function extractAccessToken(cookiesPath) {
    const raw = readFileSync(cookiesPath, 'utf-8');
    const cookies = JSON.parse(raw);

    // arena-auth-prod-v1.X parçalarını sıralı al
    const parts = cookies
        .filter(c => c.name && c.name.startsWith('arena-auth-prod-v1.') && c.value)
        .sort((a, b) => a.name.localeCompare(b.name));

    if (parts.length === 0) throw new Error('Auth cookie bulunamadı');

    // Birleştir
    const combined = parts.map(p => p.value).join('');
    const b64 = combined.replace(/^base64-/, '');
    
    // Base64 decode
    const decoded = Buffer.from(b64, 'base64').toString('utf-8');
    
    // Kontrol karakterlerini temizle
    const clean = decoded.replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, '');
    
    // JSON parse
    const session = JSON.parse(clean);
    
    return {
        access_token: session.access_token,
        refresh_token: session.refresh_token,
        expires_at: session.expires_at,
        email: session.user?.email
    };
}

// Test
const cookiesPath = process.argv[2] || '/root/Download/arena-cookies.json';
try {
    const result = extractAccessToken(cookiesPath);
    console.log('✅ Access token:', result.access_token.substring(0, 50) + '...');
    console.log('✅ Refresh token:', result.refresh_token);
    console.log('✅ Email:', result.email);
    console.log('✅ Expires at:', new Date(result.expires_at * 1000).toISOString());
} catch(e) {
    console.error('❌ Hata:', e.message);
    process.exit(1);
}
