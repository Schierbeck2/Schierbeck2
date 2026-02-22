import { prisma } from '@/lib/db';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const category = searchParams.get('category');
  const leftoverOnly = searchParams.get('leftovers') === 'true';

  const where: Record<string, unknown> = {};
  if (category) where.category = category;
  if (leftoverOnly) where.isLeftover = true;

  const items = await prisma.inventoryItem.findMany({
    where,
    orderBy: [{ expiryDate: 'asc' }, { addedAt: 'desc' }],
  });

  return NextResponse.json(items);
}

export async function POST(request: NextRequest) {
  const body = await request.json();

  const item = await prisma.inventoryItem.create({
    data: {
      name: body.name,
      category: body.category || 'fridge',
      quantity: body.quantity ?? 1,
      unit: body.unit || 'item',
      isLeftover: body.isLeftover ?? false,
      expiryDate: body.expiryDate ? new Date(body.expiryDate) : null,
      notes: body.notes || null,
    },
  });

  return NextResponse.json(item, { status: 201 });
}

export async function PUT(request: NextRequest) {
  const body = await request.json();

  if (!body.id) {
    return NextResponse.json({ error: 'id is required' }, { status: 400 });
  }

  const item = await prisma.inventoryItem.update({
    where: { id: body.id },
    data: {
      ...(body.name !== undefined && { name: body.name }),
      ...(body.category !== undefined && { category: body.category }),
      ...(body.quantity !== undefined && { quantity: body.quantity }),
      ...(body.unit !== undefined && { unit: body.unit }),
      ...(body.isLeftover !== undefined && { isLeftover: body.isLeftover }),
      ...(body.expiryDate !== undefined && {
        expiryDate: body.expiryDate ? new Date(body.expiryDate) : null,
      }),
      ...(body.notes !== undefined && { notes: body.notes }),
    },
  });

  return NextResponse.json(item);
}

export async function DELETE(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get('id');

  if (!id) {
    return NextResponse.json({ error: 'id is required' }, { status: 400 });
  }

  await prisma.inventoryItem.delete({ where: { id } });
  return NextResponse.json({ success: true });
}
