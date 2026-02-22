import { prisma } from '@/lib/db';
import { NextRequest, NextResponse } from 'next/server';

export async function GET() {
  const persons = await prisma.person.findMany({
    orderBy: { name: 'asc' },
  });

  return NextResponse.json(
    persons.map((p) => ({
      ...p,
      dietaryRestrictions: JSON.parse(p.dietaryRestrictions),
      allergies: JSON.parse(p.allergies),
      preferences: JSON.parse(p.preferences),
      dislikes: JSON.parse(p.dislikes),
    }))
  );
}

export async function POST(request: NextRequest) {
  const body = await request.json();

  const person = await prisma.person.create({
    data: {
      name: body.name,
      dietaryRestrictions: JSON.stringify(body.dietaryRestrictions || []),
      allergies: JSON.stringify(body.allergies || []),
      preferences: JSON.stringify(body.preferences || []),
      dislikes: JSON.stringify(body.dislikes || []),
      calorieTarget: body.calorieTarget || null,
    },
  });

  return NextResponse.json(
    {
      ...person,
      dietaryRestrictions: JSON.parse(person.dietaryRestrictions),
      allergies: JSON.parse(person.allergies),
      preferences: JSON.parse(person.preferences),
      dislikes: JSON.parse(person.dislikes),
    },
    { status: 201 }
  );
}

export async function PUT(request: NextRequest) {
  const body = await request.json();

  if (!body.id) {
    return NextResponse.json({ error: 'id is required' }, { status: 400 });
  }

  const data: Record<string, unknown> = {};
  if (body.name !== undefined) data.name = body.name;
  if (body.dietaryRestrictions !== undefined)
    data.dietaryRestrictions = JSON.stringify(body.dietaryRestrictions);
  if (body.allergies !== undefined)
    data.allergies = JSON.stringify(body.allergies);
  if (body.preferences !== undefined)
    data.preferences = JSON.stringify(body.preferences);
  if (body.dislikes !== undefined)
    data.dislikes = JSON.stringify(body.dislikes);
  if (body.calorieTarget !== undefined) data.calorieTarget = body.calorieTarget;

  const person = await prisma.person.update({
    where: { id: body.id },
    data,
  });

  return NextResponse.json({
    ...person,
    dietaryRestrictions: JSON.parse(person.dietaryRestrictions),
    allergies: JSON.parse(person.allergies),
    preferences: JSON.parse(person.preferences),
    dislikes: JSON.parse(person.dislikes),
  });
}

export async function DELETE(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get('id');

  if (!id) {
    return NextResponse.json({ error: 'id is required' }, { status: 400 });
  }

  await prisma.person.delete({ where: { id } });
  return NextResponse.json({ success: true });
}
