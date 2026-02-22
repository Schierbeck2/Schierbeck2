'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface InventoryItem {
  id: string;
  name: string;
  category: string;
  quantity: number;
  unit: string;
  isLeftover: boolean;
  expiryDate: string | null;
}

interface MealPlan {
  id: string;
  date: string;
  mealType: string;
  customMeal: string | null;
  recipe: { title: string } | null;
}

export default function Dashboard() {
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [todayMeals, setTodayMeals] = useState<MealPlan[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const today = new Date().toISOString().split('T')[0];
        const [invRes, mealRes] = await Promise.all([
          fetch('/api/inventory'),
          fetch(`/api/meals?start=${today}&end=${today}`),
        ]);
        if (invRes.ok) setInventory(await invRes.json());
        if (mealRes.ok) setTodayMeals(await mealRes.json());
      } catch {
        // silently handle fetch errors
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const expiringSoon = inventory.filter((item) => {
    if (!item.expiryDate) return false;
    const days = (new Date(item.expiryDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24);
    return days >= 0 && days <= 3;
  });

  const leftovers = inventory.filter((i) => i.isLeftover);
  const fridgeCount = inventory.filter((i) => i.category === 'fridge').length;
  const freezerCount = inventory.filter((i) => i.category === 'freezer').length;
  const pantryCount = inventory.filter((i) => i.category === 'pantry').length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading...</div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-20 md:pb-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">Your kitchen at a glance</p>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Link href="/inventory?category=fridge" className="card hover:shadow-md transition-shadow">
          <div className="text-3xl font-bold text-blue-600">{fridgeCount}</div>
          <div className="text-sm text-gray-500">Fridge items</div>
        </Link>
        <Link href="/inventory?category=freezer" className="card hover:shadow-md transition-shadow">
          <div className="text-3xl font-bold text-cyan-600">{freezerCount}</div>
          <div className="text-sm text-gray-500">Freezer items</div>
        </Link>
        <Link href="/inventory?category=pantry" className="card hover:shadow-md transition-shadow">
          <div className="text-3xl font-bold text-amber-600">{pantryCount}</div>
          <div className="text-sm text-gray-500">Pantry items</div>
        </Link>
        <Link href="/inventory?leftovers=true" className="card hover:shadow-md transition-shadow">
          <div className="text-3xl font-bold text-orange-600">{leftovers.length}</div>
          <div className="text-sm text-gray-500">Leftovers</div>
        </Link>
      </div>

      {/* Expiring soon */}
      {expiringSoon.length > 0 && (
        <div className="card border-amber-200 bg-amber-50">
          <h2 className="font-semibold text-amber-800 mb-3">Expiring Soon</h2>
          <div className="space-y-2">
            {expiringSoon.map((item) => (
              <div key={item.id} className="flex justify-between items-center text-sm">
                <span className="text-amber-900">{item.name}</span>
                <span className="text-amber-600">
                  {item.expiryDate
                    ? new Date(item.expiryDate).toLocaleDateString()
                    : ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Today's meals */}
      <div className="card">
        <div className="flex justify-between items-center mb-3">
          <h2 className="font-semibold text-gray-900">Today&apos;s Meals</h2>
          <Link href="/meals" className="text-sm text-primary-600 hover:text-primary-700">
            View all
          </Link>
        </div>
        {todayMeals.length === 0 ? (
          <p className="text-gray-400 text-sm">No meals planned for today.</p>
        ) : (
          <div className="space-y-2">
            {todayMeals.map((meal) => (
              <div key={meal.id} className="flex items-center gap-3 text-sm">
                <span className="badge bg-primary-100 text-primary-700 capitalize w-20 justify-center">
                  {meal.mealType}
                </span>
                <span className="text-gray-700">
                  {meal.recipe?.title || meal.customMeal || 'No details'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 gap-4">
        <Link href="/inventory" className="card hover:shadow-md transition-shadow text-center">
          <div className="text-primary-600 font-medium">Add to Inventory</div>
          <p className="text-xs text-gray-400 mt-1">Track fridge, freezer &amp; pantry</p>
        </Link>
        <Link href="/recipes" className="card hover:shadow-md transition-shadow text-center">
          <div className="text-primary-600 font-medium">Import Recipe</div>
          <p className="text-xs text-gray-400 mt-1">Paste a link to import</p>
        </Link>
      </div>
    </div>
  );
}
