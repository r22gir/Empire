import Link from "next/link";

interface LegalPageLayoutProps {
  children: React.ReactNode;
  title: string;
  lastUpdated: string;
  showToc?: boolean;
  tocItems?: Array<{ id: string; title: string }>;
}

export default function LegalPageLayout({
  children,
  title,
  lastUpdated,
  showToc = false,
  tocItems = [],
}: LegalPageLayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm no-print">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/" className="text-xl font-heading font-bold text-primary-700">
              EmpireBox
            </Link>
            <Link
              href="/"
              className="text-sm text-gray-600 hover:text-primary-700"
            >
              ← Back to Home
            </Link>
          </div>
        </div>
      </nav>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Table of Contents - Desktop Sidebar */}
          {showToc && tocItems.length > 0 && (
            <aside className="hidden lg:block w-64 flex-shrink-0 no-print">
              <div className="sticky top-8">
                <h3 className="text-sm font-semibold text-gray-900 mb-4">
                  Table of Contents
                </h3>
                <nav className="space-y-2">
                  {tocItems.map((item) => (
                    <a
                      key={item.id}
                      href={`#${item.id}`}
                      className="block text-sm text-gray-600 hover:text-primary-700 transition-colors"
                    >
                      {item.title}
                    </a>
                  ))}
                </nav>
              </div>
            </aside>
          )}

          {/* Main Content */}
          <main className="flex-1 max-w-4xl">
            <div className="bg-white shadow-sm rounded-lg p-8 legal-content">
              {/* Header */}
              <header className="mb-8 border-b pb-6">
                <h1 className="text-4xl font-heading font-bold text-gray-900 mb-4">
                  {title}
                </h1>
                <p className="text-sm text-gray-500">
                  Last Updated: {lastUpdated}
                </p>
              </header>

              {/* Mobile TOC */}
              {showToc && tocItems.length > 0 && (
                <details className="lg:hidden mb-8 p-4 bg-gray-50 rounded-lg no-print">
                  <summary className="cursor-pointer font-semibold text-gray-900">
                    Table of Contents
                  </summary>
                  <nav className="mt-4 space-y-2">
                    {tocItems.map((item) => (
                      <a
                        key={item.id}
                        href={`#${item.id}`}
                        className="block text-sm text-gray-600 hover:text-primary-700"
                      >
                        {item.title}
                      </a>
                    ))}
                  </nav>
                </details>
              )}

              {/* Content */}
              <div className="prose prose-gray max-w-none">
                {children}
              </div>

              {/* Footer */}
              <footer className="mt-12 pt-6 border-t text-center">
                <p className="text-sm text-gray-600">
                  Questions about this policy?{" "}
                  <Link href="/contact" className="text-primary-700 hover:text-primary-800">
                    Contact us
                  </Link>
                </p>
              </footer>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
