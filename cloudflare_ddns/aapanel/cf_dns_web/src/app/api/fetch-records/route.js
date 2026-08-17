import { NextResponse } from 'next/server';
import { fetchRecords } from '@/lib/updater';

export async function POST(req) {
  try {
    const { email, key, zoneId } = await req.json();
    const records = await fetchRecords(email, key, zoneId);
    return NextResponse.json({ success: true, data: records });
  } catch (err) {
    return NextResponse.json({ success: false, error: err.message });
  }
}
