import { NextResponse } from 'next/server';
import { deleteCloudflareRecord } from '@/lib/updater';

export async function POST(req) {
  try {
    const { email, key, zoneId, recordId } = await req.json();
    const result = await deleteCloudflareRecord(email, key, zoneId, recordId);
    return NextResponse.json({ success: true, data: result });
  } catch (err) {
    return NextResponse.json({ success: false, error: err.message });
  }
}
