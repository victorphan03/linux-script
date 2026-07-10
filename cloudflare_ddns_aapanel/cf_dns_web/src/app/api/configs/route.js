import { NextResponse } from 'next/server';
import { getConfigs, saveConfigs } from '@/lib/updater';

export async function GET() {
  return NextResponse.json(getConfigs());
}

export async function POST(req) {
  const data = await req.json();
  saveConfigs(data);
  return NextResponse.json({ success: true, message: 'Đã lưu cấu hình' });
}
