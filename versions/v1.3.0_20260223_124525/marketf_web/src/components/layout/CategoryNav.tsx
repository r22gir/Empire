import Link from 'next/link';

const categories = [
  { name: 'Electronics', icon: '📱', slug: 'electronics' },
  { name: 'Clothing', icon: '👗', slug: 'clothing' },
  { name: 'Home', icon: '🏠', slug: 'home' },
  { name: 'Sports', icon: '⚽', slug: 'sports' },
  { name: 'Collectibles', icon: '🎨', slug: 'collectibles' },
  { name: 'More', icon: '➕', slug: 'all' },
];

export default function CategoryNav() {
  return (
    <div className="bg-gray-50 border-y border-gray-200">
      <div className="container">
        <div className="flex items-center gap-8 py-4 overflow-x-auto">
          {categories.map((category) => (
            <Link
              key={category.slug}
              href={`/category/${category.slug}`}
              className="flex items-center gap-2 text-gray-700 hover:text-primary whitespace-nowrap"
            >
              <span className="text-xl">{category.icon}</span>
              <span className="font-medium">{category.name}</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
