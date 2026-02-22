import { prisma } from '@/lib/db';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const startDate = searchParams.get('start');
  const endDate = searchParams.get('end');

  const where: Record<string, unknown> = {};
  if (startDate && endDate) {
    where.date = {
      gte: new Date(startDate),
      lte: new Date(endDate),
    };
  } else if (startDate) {
    where.date = { gte: new Date(startDate) };
  }

  const meals = await prisma.mealPlan.findMany({
    where,
    include: {
      recipe: true,
      persons: {
        include: { person: true },
      },
    },
    orderBy: [{ date: 'asc' }, { mealType: 'asc' }],
  });

  return NextResponse.json(
    meals.map((m) => ({
      ...m,
      recipe: m.recipe
        ? {
            ...m.recipe,
            ingredients: JSON.parse(m.recipe.ingredients),
            instructions: JSON.parse(m.recipe.instructions),
            tags: JSON.parse(m.recipe.tags),
          }
        : null,
      persons: m.persons.map((p) => ({
        ...p.person,
        dietaryRestrictions: JSON.parse(p.person.dietaryRestrictions),
        allergies: JSON.parse(p.person.allergies),
        preferences: JSON.parse(p.person.preferences),
        dislikes: JSON.parse(p.person.dislikes),
      })),
    }))
  );
}

export async function POST(request: NextRequest) {
  const body = await request.json();

  const meal = await prisma.mealPlan.create({
    data: {
      date: new Date(body.date),
      mealType: body.mealType,
      recipeId: body.recipeId || null,
      customMeal: body.customMeal || null,
      notes: body.notes || null,
      persons: body.personIds?.length
        ? {
            create: body.personIds.map((personId: string) => ({
              personId,
            })),
          }
        : undefined,
    },
    include: {
      recipe: true,
      persons: { include: { person: true } },
    },
  });

  return NextResponse.json(meal, { status: 201 });
}

export async function PUT(request: NextRequest) {
  const body = await request.json();

  if (!body.id) {
    return NextResponse.json({ error: 'id is required' }, { status: 400 });
  }

  // Update person assignments if provided
  if (body.personIds) {
    await prisma.mealPlanPerson.deleteMany({
      where: { mealPlanId: body.id },
    });
    await prisma.mealPlanPerson.createMany({
      data: body.personIds.map((personId: string) => ({
        mealPlanId: body.id,
        personId,
      })),
    });
  }

  const data: Record<string, unknown> = {};
  if (body.date !== undefined) data.date = new Date(body.date);
  if (body.mealType !== undefined) data.mealType = body.mealType;
  if (body.recipeId !== undefined) data.recipeId = body.recipeId;
  if (body.customMeal !== undefined) data.customMeal = body.customMeal;
  if (body.notes !== undefined) data.notes = body.notes;

  const meal = await prisma.mealPlan.update({
    where: { id: body.id },
    data,
    include: {
      recipe: true,
      persons: { include: { person: true } },
    },
  });

  return NextResponse.json(meal);
}

export async function DELETE(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get('id');

  if (!id) {
    return NextResponse.json({ error: 'id is required' }, { status: 400 });
  }

  await prisma.mealPlan.delete({ where: { id } });
  return NextResponse.json({ success: true });
}
