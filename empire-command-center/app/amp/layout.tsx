export default function AmpLayout({ children }: { children: React.ReactNode }) {
  // Marks every /amp/* route so body:has([data-amp-page]) can scroll.
  // The operator Command Center is not under this layout.
  return <div data-amp-page>{children}</div>;
}
