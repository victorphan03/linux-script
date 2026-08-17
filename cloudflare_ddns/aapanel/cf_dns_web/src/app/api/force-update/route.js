import { NextResponse } from 'next/server';
import { checkAndUpdateDns } from '@/lib/updater';

export async function POST() {
  const results = await checkAndUpdateDns(true);
  return NextResponse.json({ success: true, results });
}
