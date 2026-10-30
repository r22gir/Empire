import type { Metadata } from 'next';
import StoreChrome from './StoreChrome';
import './store.css';

export const metadata: Metadata = {
  title: 'Empire Fine Fabrics',
  description: 'Cloth for drapery, upholstery, and outdoor work. Sold by the yard from Empire Workroom.',
};

export default function FineFabricsLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      <link
        href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=Jost:wght@300;400;500&display=swap"
        rel="stylesheet"
      />
      <StoreChrome>{children}</StoreChrome>
    </>
  );
}
