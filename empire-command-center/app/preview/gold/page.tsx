// /preview/gold: switch this browser to the gold-standard docs palette preview (color only),
// then land on the home ring. /?theme=default switches back.
import { redirect } from 'next/navigation';

export default function GoldPreview() {
  redirect('/?theme=gold');
}
