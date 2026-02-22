import { prisma } from '@/lib/db';
import { NextRequest, NextResponse } from 'next/server';

// Home Assistant webhook endpoint for voice intents and automations
export async function POST(request: NextRequest) {
  const body = await request.json();
  const { action, item, location, quantity, unit } = body;

  switch (action) {
    case 'add_item': {
      const newItem = await prisma.inventoryItem.create({
        data: {
          name: item || 'Unknown item',
          category: mapLocation(location),
          quantity: parseFloat(quantity) || 1,
          unit: unit || 'item',
        },
      });
      return NextResponse.json({
        speech: `Added ${newItem.quantity} ${newItem.unit} of ${newItem.name} to the ${newItem.category}.`,
        item: newItem,
      });
    }

    case 'remove_item': {
      const existing = await prisma.inventoryItem.findFirst({
        where: {
          name: { contains: item },
          ...(location ? { category: mapLocation(location) } : {}),
        },
      });

      if (!existing) {
        return NextResponse.json({
          speech: `I couldn't find ${item} in your inventory.`,
        });
      }

      const removeQty = parseFloat(quantity) || existing.quantity;
      if (removeQty >= existing.quantity) {
        await prisma.inventoryItem.delete({ where: { id: existing.id } });
        return NextResponse.json({
          speech: `Removed ${existing.name} from the ${existing.category}.`,
        });
      } else {
        const updated = await prisma.inventoryItem.update({
          where: { id: existing.id },
          data: { quantity: existing.quantity - removeQty },
        });
        return NextResponse.json({
          speech: `Updated ${updated.name} to ${updated.quantity} ${updated.unit} in the ${updated.category}.`,
          item: updated,
        });
      }
    }

    case 'list_items': {
      const category = location ? mapLocation(location) : undefined;
      const items = await prisma.inventoryItem.findMany({
        where: category ? { category } : {},
        orderBy: { name: 'asc' },
      });

      if (items.length === 0) {
        const loc = category || 'inventory';
        return NextResponse.json({
          speech: `Your ${loc} is empty.`,
        });
      }

      const names = items.map((i) => `${i.quantity} ${i.unit} of ${i.name}`);
      const loc = category || 'inventory';
      return NextResponse.json({
        speech: `You have ${items.length} items in the ${loc}: ${names.slice(0, 5).join(', ')}${items.length > 5 ? ` and ${items.length - 5} more` : ''}.`,
        items,
      });
    }

    case 'expiring_soon': {
      const threeDays = new Date();
      threeDays.setDate(threeDays.getDate() + 3);

      const items = await prisma.inventoryItem.findMany({
        where: {
          expiryDate: {
            lte: threeDays,
            gte: new Date(),
          },
        },
        orderBy: { expiryDate: 'asc' },
      });

      if (items.length === 0) {
        return NextResponse.json({
          speech: 'Nothing is expiring in the next 3 days.',
        });
      }

      const names = items.map((i) => i.name);
      return NextResponse.json({
        speech: `${items.length} items expiring soon: ${names.join(', ')}.`,
        items,
      });
    }

    case 'add_leftover': {
      const leftover = await prisma.inventoryItem.create({
        data: {
          name: item || 'Leftovers',
          category: mapLocation(location) || 'fridge',
          quantity: parseFloat(quantity) || 1,
          unit: unit || 'serving',
          isLeftover: true,
          expiryDate: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000), // 3 days
        },
      });
      return NextResponse.json({
        speech: `Saved ${leftover.name} as leftovers in the ${leftover.category}.`,
        item: leftover,
      });
    }

    default:
      return NextResponse.json(
        { error: 'Unknown action', speech: "I didn't understand that command." },
        { status: 400 }
      );
  }
}

function mapLocation(location?: string): string {
  if (!location) return 'fridge';
  const loc = location.toLowerCase();
  if (loc.includes('freeze')) return 'freezer';
  if (loc.includes('pantry') || loc.includes('cabinet') || loc.includes('cupboard'))
    return 'pantry';
  return 'fridge';
}
