import { scrapeRecipe } from '@/lib/recipe-scraper';
import { prisma } from '@/lib/db';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { url, save } = body;

  if (!url) {
    return NextResponse.json({ error: 'url is required' }, { status: 400 });
  }

  try {
    const scraped = await scrapeRecipe(url);

    if (save) {
      const recipe = await prisma.recipe.create({
        data: {
          title: scraped.title,
          sourceUrl: url,
          ingredients: JSON.stringify(scraped.ingredients),
          instructions: JSON.stringify(scraped.instructions),
          servings: scraped.servings || null,
          prepTime: scraped.prepTime || null,
          cookTime: scraped.cookTime || null,
          tags: JSON.stringify(scraped.tags || []),
          imageUrl: scraped.imageUrl || null,
        },
      });

      return NextResponse.json({
        ...recipe,
        ingredients: JSON.parse(recipe.ingredients),
        instructions: JSON.parse(recipe.instructions),
        tags: JSON.parse(recipe.tags),
      }, { status: 201 });
    }

    return NextResponse.json(scraped);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to scrape recipe';
    return NextResponse.json({ error: message }, { status: 422 });
  }
}
