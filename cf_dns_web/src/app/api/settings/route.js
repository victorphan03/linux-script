import { NextResponse } from 'next/server';
import { getSettings, saveSettings } from '@/lib/updater';

export async function GET() {
  return NextResponse.json(getSettings());
}

export async function POST(req) {
  const data = await req.json();
  saveSettings(data);
  return NextResponse.json({ success: true, message: 'Đã lưu thời gian quét' });
}
