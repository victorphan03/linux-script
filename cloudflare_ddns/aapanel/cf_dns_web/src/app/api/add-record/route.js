import { NextResponse } from 'next/server';
import { addCloudflareRecord } from '@/lib/updater';

export async function POST(req) {
  try {
    const { email, key, zoneId, recordName, content, proxied } = await req.json();
    const result = await addCloudflareRecord(email, key, zoneId, recordName, content, proxied);
    return NextResponse.json({ success: true, data: result });
  } catch (err) {
    return NextResponse.json({ success: false, error: err.message });
  }
}
