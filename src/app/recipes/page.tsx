'use client';

import { useEffect, useState, useCallback } from 'react';

interface Recipe {
  id: string;
  title: string;
  sourceUrl: string | null;
  ingredients: string[];
  instructions: string[];
  servings: number | null;
  prepTime: number | null;
  cookTime: number | null;
  tags: string[];
  imageUrl: string | null;
  createdAt: string;
}

export default function RecipesPage() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [search, setSearch] = useState('');
  const [importUrl, setImportUrl] = useState('');
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState('');
  const [showManualForm, setShowManualForm] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [manualForm, setManualForm] = useState({
    title: '',
    ingredients: '',
    instructions: '',
    servings: '',
    prepTime: '',
    cookTime: '',
    tags: '',
    sourceUrl: '',
  });

  const loadRecipes = useCallback(async () => {
    const params = search ? `?search=${encodeURIComponent(search)}` : '';
    const res = await fetch(`/api/recipes${params}`);
    if (res.ok) setRecipes(await res.json());
  }, [search]);

  useEffect(() => {
    loadRecipes();
  }, [loadRecipes]);

  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!importUrl) return;

    setImporting(true);
    setImportError('');

    try {
      const res = await fetch('/api/recipes/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: importUrl, save: true }),
      });

      if (res.ok) {
        setImportUrl('');
        loadRecipes();
      } else {
        const data = await res.json();
        setImportError(data.error || 'Failed to import recipe');
      }
    } catch {
      setImportError('Network error. Please try again.');
    } finally {
      setImporting(false);
    }
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      title: manualForm.title,
      ingredients: manualForm.ingredients.split('\n').map((s) => s.trim()).filter(Boolean),
      instructions: manualForm.instructions.split('\n').map((s) => s.trim()).filter(Boolean),
      servings: manualForm.servings ? parseInt(manualForm.servings, 10) : null,
      prepTime: manualForm.prepTime ? parseInt(manualForm.prepTime, 10) : null,
      cookTime: manualForm.cookTime ? parseInt(manualForm.cookTime, 10) : null,
      tags: manualForm.tags ? manualForm.tags.split(',').map((s) => s.trim()).filter(Boolean) : [],
      sourceUrl: manualForm.sourceUrl || null,
    };

    const res = await fetch('/api/recipes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      setManualForm({ title: '', ingredients: '', instructions: '', servings: '', prepTime: '', cookTime: '', tags: '', sourceUrl: '' });
      setShowManualForm(false);
      loadRecipes();
    }
  };

  const handleDelete = async (id: string) => {
    const res = await fetch(`/api/recipes?id=${id}`, { method: 'DELETE' });
    if (res.ok) loadRecipes();
  };

  const formatTime = (minutes: number | null) => {
    if (!minutes) return null;
    if (minutes < 60) return `${minutes}m`;
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return m ? `${h}h ${m}m` : `${h}h`;
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-20 md:pb-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Recipes</h1>
        <p className="text-gray-500 mt-1">Import recipes from links or add them manually</p>
      </div>

      {/* Import by URL */}
      <form onSubmit={handleImport} className="card">
        <h3 className="font-semibold mb-3">Import from Link</h3>
        <div className="flex gap-2">
          <input
            type="url"
            value={importUrl}
            onChange={(e) => setImportUrl(e.target.value)}
            className="input flex-1"
            placeholder="Paste a recipe URL (e.g., allrecipes.com/recipe/...)"
            required
          />
          <button type="submit" className="btn-primary whitespace-nowrap" disabled={importing}>
            {importing ? 'Importing...' : 'Import'}
          </button>
        </div>
        {importError && (
          <p className="text-red-500 text-sm mt-2">{importError}</p>
        )}
      </form>

      {/* Actions bar */}
      <div className="flex gap-2 flex-wrap">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input flex-1 min-w-[200px]"
          placeholder="Search recipes..."
        />
        <button
          onClick={() => setShowManualForm(!showManualForm)}
          className="btn-secondary"
        >
          {showManualForm ? 'Cancel' : '+ Add Manually'}
        </button>
      </div>

      {/* Manual form */}
      {showManualForm && (
        <form onSubmit={handleManualSubmit} className="card space-y-4">
          <h3 className="font-semibold">Add Recipe Manually</h3>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
            <input
              type="text"
              value={manualForm.title}
              onChange={(e) => setManualForm({ ...manualForm, title: e.target.value })}
              className="input"
              placeholder="Recipe name"
              required
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Servings</label>
              <input
                type="number"
                value={manualForm.servings}
                onChange={(e) => setManualForm({ ...manualForm, servings: e.target.value })}
                className="input"
                placeholder="4"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Prep Time (min)</label>
              <input
                type="number"
                value={manualForm.prepTime}
                onChange={(e) => setManualForm({ ...manualForm, prepTime: e.target.value })}
                className="input"
                placeholder="15"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Cook Time (min)</label>
              <input
                type="number"
                value={manualForm.cookTime}
                onChange={(e) => setManualForm({ ...manualForm, cookTime: e.target.value })}
                className="input"
                placeholder="30"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Ingredients <span className="text-gray-400 font-normal">(one per line)</span>
            </label>
            <textarea
              value={manualForm.ingredients}
              onChange={(e) => setManualForm({ ...manualForm, ingredients: e.target.value })}
              className="input h-32"
              placeholder={"2 cups flour\n1 tsp salt\n3 eggs"}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Instructions <span className="text-gray-400 font-normal">(one step per line)</span>
            </label>
            <textarea
              value={manualForm.instructions}
              onChange={(e) => setManualForm({ ...manualForm, instructions: e.target.value })}
              className="input h-32"
              placeholder={"Preheat oven to 350F\nMix dry ingredients\nAdd wet ingredients"}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tags <span className="text-gray-400 font-normal">(comma-separated)</span>
            </label>
            <input
              type="text"
              value={manualForm.tags}
              onChange={(e) => setManualForm({ ...manualForm, tags: e.target.value })}
              className="input"
              placeholder="Italian, Pasta, Quick"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Source URL (optional)</label>
            <input
              type="url"
              value={manualForm.sourceUrl}
              onChange={(e) => setManualForm({ ...manualForm, sourceUrl: e.target.value })}
              className="input"
              placeholder="https://..."
            />
          </div>
          <button type="submit" className="btn-primary">Save Recipe</button>
        </form>
      )}

      {/* Recipe list */}
      {recipes.length === 0 ? (
        <div className="card text-center text-gray-400 py-12">
          <p>No recipes yet. Import one from a URL or add it manually.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {recipes.map((recipe) => (
            <div key={recipe.id} className="card">
              <div className="flex items-start justify-between">
                <div
                  className="flex-1 cursor-pointer"
                  onClick={() => setExpandedId(expandedId === recipe.id ? null : recipe.id)}
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold text-gray-900">{recipe.title}</h3>
                    {recipe.tags.map((tag) => (
                      <span key={tag} className="badge bg-gray-100 text-gray-600">{tag}</span>
                    ))}
                  </div>
                  <div className="flex items-center gap-3 text-sm text-gray-500 mt-1">
                    {recipe.servings && <span>{recipe.servings} servings</span>}
                    {recipe.prepTime && <span>Prep: {formatTime(recipe.prepTime)}</span>}
                    {recipe.cookTime && <span>Cook: {formatTime(recipe.cookTime)}</span>}
                    {recipe.sourceUrl && (
                      <a
                        href={recipe.sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary-600 hover:underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        Source
                      </a>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(recipe.id)}
                  className="p-2 text-gray-400 hover:text-red-500"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>

              {/* Expanded details */}
              {expandedId === recipe.id && (
                <div className="mt-4 pt-4 border-t border-gray-100 space-y-4">
                  {recipe.ingredients.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-2">Ingredients</h4>
                      <ul className="list-disc list-inside text-sm text-gray-600 space-y-0.5">
                        {recipe.ingredients.map((ing, i) => (
                          <li key={i}>{ing}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {recipe.instructions.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-2">Instructions</h4>
                      <ol className="list-decimal list-inside text-sm text-gray-600 space-y-1">
                        {recipe.instructions.map((step, i) => (
                          <li key={i}>{step}</li>
                        ))}
                      </ol>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
