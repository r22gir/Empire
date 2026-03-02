import SetupWizard from '@/components/SetupWizard';

interface Props {
  params: Promise<{ id: string }>;
}

export default async function DeviceSetupPage({ params }: Props) {
  const { id } = await params;
  return <SetupWizard deviceId={id} />;
}
