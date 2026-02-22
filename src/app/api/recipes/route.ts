import { prisma } from '@/lib/db';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const search = searchParams.get('search');

  const where = search
    ? { title: { contains: search } }
    : {};

  const recipes = await prisma.recipe.findMany({
    where,
    orderBy: { createdAt: 'desc' },
  });

  return NextResponse.json(
    recipes.map((r) => ({
      ...r,
      ingredients: JSON.parse(r.ingredients),
      instructions: JSON.parse(r.instructions),
      tags: JSON.parse(r.tags),
    }))
  );
}

export async function POST(request: NextRequest) {
  const body = await request.json();

  const recipe = await prisma.recipe.create({
    data: {
      title: body.title,
      sourceUrl: body.sourceUrl || null,
      ingredients: JSON.stringify(body.ingredients || []),
      instructions: JSON.stringify(body.instructions || []),
      servings: body.servings || null,
      prepTime: body.prepTime || null,
      cookTime: body.cookTime || null,
      tags: JSON.stringify(body.tags || []),
      imageUrl: body.imageUrl || null,
    },
  });

  return NextResponse.json(
    {
      ...recipe,
      ingredients: JSON.parse(recipe.ingredients),
      instructions: JSON.parse(recipe.instructions),
      tags: JSON.parse(recipe.tags),
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
  if (body.title !== undefined) data.title = body.title;
  if (body.sourceUrl !== undefined) data.sourceUrl = body.sourceUrl;
  if (body.ingredients !== undefined) data.ingredients = JSON.stringify(body.ingredients);
  if (body.instructions !== undefined) data.instructions = JSON.stringify(body.instructions);
  if (body.servings !== undefined) data.servings = body.servings;
  if (body.prepTime !== undefined) data.prepTime = body.prepTime;
  if (body.cookTime !== undefined) data.cookTime = body.cookTime;
  if (body.tags !== undefined) data.tags = JSON.stringify(body.tags);
  if (body.imageUrl !== undefined) data.imageUrl = body.imageUrl;

  const recipe = await prisma.recipe.update({
    where: { id: body.id },
    data,
  });

  return NextResponse.json({
    ...recipe,
    ingredients: JSON.parse(recipe.ingredients),
    instructions: JSON.parse(recipe.instructions),
    tags: JSON.parse(recipe.tags),
  });
}

export async function DELETE(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get('id');

  if (!id) {
    return NextResponse.json({ error: 'id is required' }, { status: 400 });
  }

  await prisma.recipe.delete({ where: { id } });
  return NextResponse.json({ success: true });
}
