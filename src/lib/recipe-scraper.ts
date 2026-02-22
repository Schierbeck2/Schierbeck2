import * as cheerio from 'cheerio';

interface ScrapedRecipe {
  title: string;
  ingredients: string[];
  instructions: string[];
  servings?: number;
  prepTime?: number;
  cookTime?: number;
  imageUrl?: string;
  tags?: string[];
}

function parseDuration(iso8601: string): number | undefined {
  if (!iso8601) return undefined;
  const match = iso8601.match(/PT(?:(\d+)H)?(?:(\d+)M)?/);
  if (!match) return undefined;
  const hours = parseInt(match[1] || '0', 10);
  const minutes = parseInt(match[2] || '0', 10);
  return hours * 60 + minutes;
}

function extractJsonLd(html: string): ScrapedRecipe | null {
  const $ = cheerio.load(html);
  const scripts = $('script[type="application/ld+json"]');

  for (let i = 0; i < scripts.length; i++) {
    try {
      const text = $(scripts[i]).html();
      if (!text) continue;

      let data = JSON.parse(text);

      // Handle @graph arrays
      if (data['@graph']) {
        data = data['@graph'].find(
          (item: Record<string, unknown>) =>
            item['@type'] === 'Recipe' ||
            (Array.isArray(item['@type']) && item['@type'].includes('Recipe'))
        );
        if (!data) continue;
      }

      // Handle arrays at top level
      if (Array.isArray(data)) {
        data = data.find(
          (item: Record<string, unknown>) =>
            item['@type'] === 'Recipe' ||
            (Array.isArray(item['@type']) && item['@type'].includes('Recipe'))
        );
        if (!data) continue;
      }

      const type = data['@type'];
      if (type !== 'Recipe' && !(Array.isArray(type) && type.includes('Recipe'))) {
        continue;
      }

      const ingredients: string[] = Array.isArray(data.recipeIngredient)
        ? data.recipeIngredient
        : [];

      let instructions: string[] = [];
      if (Array.isArray(data.recipeInstructions)) {
        instructions = data.recipeInstructions.map(
          (step: string | { text?: string; '@type'?: string }) => {
            if (typeof step === 'string') return step;
            return step.text || '';
          }
        ).filter(Boolean);
      } else if (typeof data.recipeInstructions === 'string') {
        instructions = [data.recipeInstructions];
      }

      const imageUrl = typeof data.image === 'string'
        ? data.image
        : Array.isArray(data.image)
          ? data.image[0]
          : data.image?.url;

      const tags: string[] = [];
      if (data.recipeCategory) {
        const cats = Array.isArray(data.recipeCategory) ? data.recipeCategory : [data.recipeCategory];
        tags.push(...cats);
      }
      if (data.recipeCuisine) {
        const cuisines = Array.isArray(data.recipeCuisine) ? data.recipeCuisine : [data.recipeCuisine];
        tags.push(...cuisines);
      }
      if (data.keywords) {
        if (typeof data.keywords === 'string') {
          tags.push(...data.keywords.split(',').map((k: string) => k.trim()));
        } else if (Array.isArray(data.keywords)) {
          tags.push(...data.keywords);
        }
      }

      return {
        title: data.name || 'Untitled Recipe',
        ingredients,
        instructions,
        servings: data.recipeYield
          ? parseInt(String(data.recipeYield), 10) || undefined
          : undefined,
        prepTime: parseDuration(data.prepTime),
        cookTime: parseDuration(data.cookTime),
        imageUrl: typeof imageUrl === 'string' ? imageUrl : undefined,
        tags: tags.length > 0 ? tags : undefined,
      };
    } catch {
      continue;
    }
  }

  return null;
}

function extractFromMeta(html: string): ScrapedRecipe | null {
  const $ = cheerio.load(html);

  const title =
    $('meta[property="og:title"]').attr('content') ||
    $('title').text() ||
    $('h1').first().text();

  if (!title) return null;

  const imageUrl = $('meta[property="og:image"]').attr('content');

  // Try to find ingredient lists
  const ingredients: string[] = [];
  $('[class*="ingredient"], [data-ingredient]').each((_, el) => {
    const text = $(el).text().trim();
    if (text && text.length < 200) {
      ingredients.push(text);
    }
  });

  // Try to find instruction lists
  const instructions: string[] = [];
  $('[class*="instruction"], [class*="direction"], [class*="step"]').each((_, el) => {
    const text = $(el).text().trim();
    if (text && text.length < 1000) {
      instructions.push(text);
    }
  });

  return {
    title: title.trim(),
    ingredients,
    instructions,
    imageUrl: imageUrl || undefined,
  };
}

export async function scrapeRecipe(url: string): Promise<ScrapedRecipe> {
  const response = await fetch(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (compatible; HomeFoodManager/1.0)',
      Accept: 'text/html',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch recipe: ${response.status} ${response.statusText}`);
  }

  const html = await response.text();

  // Try JSON-LD first (most reliable)
  const jsonLdRecipe = extractJsonLd(html);
  if (jsonLdRecipe) return jsonLdRecipe;

  // Fall back to meta tags and class-based extraction
  const metaRecipe = extractFromMeta(html);
  if (metaRecipe) return metaRecipe;

  throw new Error('Could not extract recipe data from this URL. The page may not contain structured recipe data.');
}
