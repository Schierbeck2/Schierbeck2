import type { Metadata } from 'next';
import './globals.css';
import Navigation from '@/components/Navigation';

export const metadata: Metadata = {
  title: 'Home Food Manager',
  description: 'Manage your household food inventory, meal plans, and recipes',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">
        <div className="flex flex-col md:flex-row min-h-screen">
          <Navigation />
          <main className="flex-1 p-4 md:p-6 md:ml-64">{children}</main>
        </div>
      </body>
    </html>
  );
}
