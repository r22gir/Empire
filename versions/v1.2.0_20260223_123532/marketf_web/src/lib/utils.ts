export function formatPrice(price: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(price);
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(date));
}

export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}

export function truncate(text: string, length: number): string {
  if (text.length <= length) return text;
  return text.slice(0, length) + '...';
}

export function calculateMarketFee(price: number): number {
  return price * 0.08;
}

export function calculatePaymentFee(price: number): number {
  return price * 0.029 + 0.30;
}

export function calculateSellerPayout(price: number): number {
  return price - calculateMarketFee(price) - calculatePaymentFee(price);
}
