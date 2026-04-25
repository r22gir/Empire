'use client';
import React, { useState, useEffect } from 'react';
import { API } from '../../lib/api';
import {
  FileText, Globe, Package, Users, DollarSign, Clock, CheckCircle,
  Truck, Search, Plus, Building, Shield, ChevronRight, ChevronDown,
  ChevronUp, Mail, Phone, User, Loader2, AlertTriangle, ExternalLink,
  Hash, X, Zap, MapPin, ArrowRight, Star, Calendar, Eye, BookOpen,
  FileAudio
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import { PaymentModule } from '../business/payments';

// Stamp doesn't exist in lucide-react, use Shield as substitute
const Stamp = Shield;
const StampIcon = Shield;

// ============ TYPES ============

interface ApostOrder {
  id: string;
  orderNumber: string;
  customer: { name: string; email: string; phone: string };
  documents: ApostDocument[];
  status: 'received' | 'processing' | 'at_state' | 'completed' | 'shipped';
  rush: boolean;
  sameDay: boolean;
  total: number;
  paid: boolean;
  shippingMethod: string;
  shippingAddress: string;
  createdAt: string;
  trackingNumber?: string;
  attachments: Attachment[];
}

interface Attachment {
  id: string;
  filename: string;
  stored_as: string;
  content_type: string;
  size: number;
  uploaded_at: string;
}

interface ApostDocument {
  id: string;
  type: string;
  description: string;
  stateOfOrigin: string;
  destinationCountry: string;
  needsNotarization: boolean;
  needsCertification: boolean;
  status: 'received' | 'notarized' | 'at_state' | 'apostilled' | 'shipped' | 'delivered';
  trackingNumber?: string;
}

interface ApostCustomer {
  id: string;
  name: string;
  email: string;
  phone: string;
  totalOrders: number;
  totalSpent: number;
  orders: ApostOrder[];
}

interface IntakeClient {
  id: string;
  fullName: string;
  dateOfBirth: string;
  ssnLast4: string;
  nationality: string;
  gender: string;
  email: string;
  phone: string;
  street: string;
  city: string;
  state: string;
  zip: string;
  country: string;
  idType: string;
  idNumber: string;
  idIssueDate: string;
  idExpiryDate: string;
  idIssuingAuthority: string;
  documents: IntakeDocument[];
  urgency: 'standard' | 'rush' | 'same-day';
  paymentPreference: 'pay-now' | 'pay-later' | 'invoice';
  referralSource: string;
  notes: string;
  createdAt: string;
}

interface IntakeDocument {
  docType: string;
  originalLanguage: string;
  destinationCountry: string;
  purpose: string;
  copies: number;
  needsNotarization: boolean;
  signerName: string;
  signerPresent: boolean;
}

interface FormEntry {
  name: string;
  agency: string;
  purpose: string;
  url: string;
  fields: string[];
  fee: string;
}

interface ESignDocument {
  id: string;
  name: string;
  recipient: string;
  sentDate: string;
  deadline: string;
  status: 'pending' | 'viewed' | 'signed' | 'declined';
  platform: string;
}

interface CourierContact {
  id: string;
  name: string;
  company: string;
  phone: string;
  email: string;
  states: string[];
  services: string[];
  rating: number;
}

interface CourierDelivery {
  id: string;
  courier: string;
  orderNumber: string;
  pickup: string;
  destination: string;
  status: 'pickup-scheduled' | 'in-transit' | 'delivered';
  eta: string;
}

// ============ FORMS LIBRARY DATA ============

const FORMS_LIBRARY: FormEntry[] = [
  { name: 'DS-4194', agency: 'US Dept of State', purpose: 'Federal Apostille Request', url: 'https://travel.state.gov/content/travel/en/records-and-authentications/authenticate-your-document/apostille-requirements.html', fields: ['applicant_name', 'document_type', 'date_of_document', 'destination_country'], fee: '$20' },
  { name: 'DC Apostille Request', agency: 'DC Secretary of State', purpose: 'DC state document authentication', url: '', fields: ['name', 'address', 'document_description', 'notary_info'], fee: '$15' },
  { name: 'MD Authentication Request', agency: 'MD Secretary of State', purpose: 'Maryland document authentication', url: '', fields: ['applicant', 'document_type', 'notary_county'], fee: '$5-22' },
  { name: 'VA Authentication Request', agency: 'VA Secretary of Commonwealth', purpose: 'Virginia document authentication', url: '', fields: ['requester', 'document_info', 'notary_details'], fee: '$10' },
  { name: 'FBI Identity History (FD-258)', agency: 'FBI/DOJ', purpose: 'FBI background check for federal apostille', url: '', fields: ['name', 'dob', 'ssn', 'address', 'fingerprints'], fee: '$18' },
  { name: 'SS-4 (EIN Application)', agency: 'IRS', purpose: 'Employer ID for business docs', url: '', fields: ['business_name', 'type', 'address', 'responsible_party'], fee: 'Free' },
  { name: 'Vital Records Request - DC', agency: 'DC Vital Records', purpose: 'Birth/Death/Marriage cert', url: '', fields: ['type', 'person_name', 'date', 'relationship'], fee: '$22-28' },
  { name: 'Vital Records Request - MD', agency: 'MD Vital Records', purpose: 'Birth/Death/Marriage cert', url: '', fields: ['type', 'person_name', 'date', 'purpose'], fee: '$24' },
  { name: 'Vital Records Request - VA', agency: 'VA Vital Records', purpose: 'Birth/Death/Marriage cert', url: '', fields: ['type', 'person_name', 'date', 'relationship'], fee: '$12' },
  { name: 'Notarial Certificate', agency: 'Internal', purpose: 'Notarial acknowledgment certificate', url: '', fields: ['signer_name', 'date', 'notary_name', 'commission_expiry', 'state'], fee: 'Included' },
];

const ESIGN_PLATFORMS = [
  { name: 'DocuSign', price: '$25/mo', features: 'Industry standard, audit trail, templates', integration: 'API ready' },
  { name: 'HelloSign (Dropbox Sign)', price: '$20/mo', features: 'Simple, developer-friendly API', integration: 'API ready' },
  { name: 'PandaDoc', price: '$35/mo', features: 'Proposals + e-sign, CRM integration', integration: 'API ready' },
  { name: 'SignNow', price: '$18/mo', features: 'Budget-friendly, team features', integration: 'API ready' },
  { name: 'Adobe Acrobat Sign', price: '$30/mo', features: 'PDF native, enterprise', integration: 'API ready' },
];

const RON_PLATFORMS = [
  { name: 'Notarize.com', description: 'Leading RON platform, $25/session, integrates with our workflow', price: '$25/session' },
  { name: 'DocuSign Notary', description: '$25/session, part of DocuSign suite', price: '$25/session' },
  { name: 'Proof.com', description: 'Enterprise RON, bulk pricing (formerly Notarize for Business)', price: 'Custom' },
  { name: 'OneNotary', description: '$20/session, fast onboarding', price: '$20/session' },
];

const RON_STATES = [
  { state: 'DC', authorized: 'Yes', since: '2022', notes: 'Authorized under DC emergency and permanent legislation' },
  { state: 'MD', authorized: 'Yes', since: '2020', notes: 'Authorized under MD Senate Bill 734' },
  { state: 'VA', authorized: 'Yes', since: '2012', notes: 'Pioneer state — first to authorize RON in the US' },
];

// Mock/fallback data removed — all data fetched from backend APIs

// ============ NAV SECTIONS ============

const NAV_SECTIONS = [
  { id: 'overview', label: 'Overview', icon: Globe },
  { id: 'orders', label: 'Orders', icon: FileText },
  { id: 'new-order', label: 'New Order', icon: Plus },
  { id: 'customers', label: 'Customers', icon: Users },
  { id: 'pricing', label: 'Pricing', icon: DollarSign },
  { id: 'llc-integration', label: 'LLC Integration', icon: Building },
  { id: 'tracking', label: 'Tracking', icon: Package },
  { id: 'intake', label: 'Client Intake', icon: User },
  { id: 'forms', label: 'Forms Library', icon: FileText },
  { id: 'ai-fill', label: 'AI Form Assist', icon: Zap },
  { id: 'notary', label: 'Remote Notary', icon: Shield },
  { id: 'e-sign', label: 'E-Signatures', icon: CheckCircle },
  { id: 'couriers', label: 'Couriers', icon: Truck },
  { id: 'payments', label: 'Payments', icon: DollarSign },
  { id: 'docs', label: 'Docs', icon: BookOpen },
  { id: 'transcript', label: 'TranscriptForge', icon: <FileAudio size={16} /> },
] as const;

type Section = typeof NAV_SECTIONS[number]['id'];

// ============ CONSTANTS ============

const STATUS_COLORS: Record<string, { bg: string; color: string; label: string }> = {
  received: { bg: '#f3f4f6', color: '#6b7280', label: 'Received' },
  processing: { bg: '#dbeafe', color: '#2563eb', label: 'Processing' },
  at_state: { bg: '#fdf8eb', color: '#b8960c', label: 'At State' },
  completed: { bg: '#dcfce7', color: '#16a34a', label: 'Completed' },
  shipped: { bg: '#ede9fe', color: '#7c3aed', label: 'Shipped' },
  notarized: { bg: '#dbeafe', color: '#2563eb', label: 'Notarized' },
  apostilled: { bg: '#dcfce7', color: '#16a34a', label: 'Apostilled' },
  delivered: { bg: '#d1fae5', color: '#065f46', label: 'Delivered' },
};

const DOC_TYPES = [
  'Birth Certificate', 'Death Certificate', 'Marriage Certificate', 'Divorce Decree',
  'Diploma / Degree', 'Transcript', 'Power of Attorney', 'Corporate Documents',
  'Articles of Organization', 'Certificate of Good Standing', 'Operating Agreement',
  'FBI Background Check', 'Court Order', 'Affidavit', 'Notarized Document', 'Other',
];

const US_STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','DC','FL','GA','HI','ID','IL','IN','IA',
  'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM',
  'NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA',
  'WV','WI','WY',
];

const SHIPPING_METHODS = [
  { id: 'standard', label: 'USPS Priority Mail (3-5 days)', fee: 12 },
  { id: 'express', label: 'USPS Express Mail (1-2 days)', fee: 28 },
  { id: 'fedex', label: 'FedEx Overnight', fee: 45 },
  { id: 'international', label: 'International Priority', fee: 65 },
  { id: 'pickup', label: 'Local Pickup (DC Office)', fee: 0 },
];

const PRICING_TABLE = [
  { service: 'State Apostille', baseFee: 75, stateFees: { DC: 15, MD: 5, VA: 10 }, time: '5-10 business days' },
  { service: 'Federal Apostille (DS-4194)', baseFee: 99, stateFees: { DC: 20, MD: 20, VA: 20 }, time: '5-11 weeks' },
  { service: 'Embassy Legalization', baseFee: 149, stateFees: { DC: 0, MD: 0, VA: 0 }, time: '2-6 weeks' },
  { service: 'Notarization', baseFee: 25, stateFees: { DC: 0, MD: 0, VA: 0 }, time: 'Same day' },
  { service: 'Certified Copy Request', baseFee: 39, stateFees: { DC: 50, MD: 20, VA: 6 }, time: '3-10 business days' },
  { service: 'Vital Records + Apostille', baseFee: 89, stateFees: { DC: 15, MD: 15, VA: 22 }, time: '7-14 business days' },
  { service: 'FBI Background + Apostille', baseFee: 149, stateFees: { DC: 38, MD: 38, VA: 38 }, time: '6-14 weeks' },
  { service: 'Rush Processing (+)', baseFee: 50, stateFees: { DC: 0, MD: 0, VA: 0 }, time: 'Expedited' },
  { service: 'Same-Day (DC only)', baseFee: 100, stateFees: { DC: 0, MD: 0, VA: 0 }, time: 'Same day' },
];

const TRACKING_STEPS = [
  { key: 'received', label: 'Received', icon: FileText },
  { key: 'notarized', label: 'Notarized', icon: StampIcon },
  { key: 'at_state', label: 'At State', icon: Building },
  { key: 'apostilled', label: 'Apostilled', icon: CheckCircle },
  { key: 'shipped', label: 'Shipped', icon: Truck },
  { key: 'delivered', label: 'Delivered', icon: Package },
];

// Fallback data removed — all data fetched from backend APIs

// ============ COMPONENT ============

export default function ApostAppPage({ onNavigate }: { onNavigate?: (product: string, screen?: string, section?: string) => void }) {
  const [activeSection, setActiveSection] = useState<Section>('overview');
  const [orders, setOrders] = useState<ApostOrder[]>([]);
  const [customers, setCustomers] = useState<ApostCustomer[]>([]);
  const [loading, setLoading] = useState(true);
  const [ordersError, setOrdersError] = useState<string | null>(null);
  const [llcOrders, setLlcOrders] = useState<{ id: string; company: string; state: string; status: string; documents: string[] }[]>([]);
  const [courierContacts, setCourierContacts] = useState<CourierContact[]>([]);
  const [courierDeliveries, setCourierDeliveries] = useState<CourierDelivery[]>([]);
  const [expandedOrder, setExpandedOrder] = useState<string | null>(null);
  const [orderFilter, setOrderFilter] = useState<string>('all');
  const [customerSearch, setCustomerSearch] = useState('');
  const [trackingQuery, setTrackingQuery] = useState('');
  const [trackingResult, setTrackingResult] = useState<ApostOrder | null>(null);
  const [selectedCustomer, setSelectedCustomer] = useState<ApostCustomer | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Intake form state
  const [intakeForm, setIntakeForm] = useState<Omit<IntakeClient, 'id' | 'createdAt'>>({
    fullName: '', dateOfBirth: '', ssnLast4: '', nationality: '', gender: '',
    email: '', phone: '', street: '', city: '', state: '', zip: '', country: 'US',
    idType: 'passport', idNumber: '', idIssueDate: '', idExpiryDate: '', idIssuingAuthority: '',
    documents: [], urgency: 'standard', paymentPreference: 'pay-now', referralSource: '', notes: '',
  });
  const [savedClients, setSavedClients] = useState<IntakeClient[]>([]);
  const [formsSearch, setFormsSearch] = useState('');
  const [aiFillForm, setAiFillForm] = useState<string>('');
  const [aiFillClient, setAiFillClient] = useState<string>('');
  const [aiFillOrder, setAiFillOrder] = useState<string>('');
  const [aiFillFields, setAiFillFields] = useState<Record<string, string>>({});
  const [aiFillGenerated, setAiFillGenerated] = useState(false);
  const [ronSessionForm, setRonSessionForm] = useState({ clientName: '', docType: '', preferredDate: '', preferredTime: '', state: 'DC' });
  const [eSignForm, setESignForm] = useState({ documentName: '', recipientEmail: '', message: '', deadline: '' });
  const [eSignDocs, setESignDocs] = useState<ESignDocument[]>([]);
  const [courierSearch, setCourierSearch] = useState('');
  const [courierStateFilter, setCourierStateFilter] = useState('all');
  const [courierServiceFilter, setCourierServiceFilter] = useState('all');

  // Load saved clients from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem('apostapp-intake-clients');
      if (stored) setSavedClients(JSON.parse(stored));
    } catch {}
  }, []);

  // New Order form state
  const [newOrder, setNewOrder] = useState({
    customerName: '', customerEmail: '', customerPhone: '',
    documents: [] as { type: string; description: string; stateOfOrigin: string; destinationCountry: string; needsNotarization: boolean; needsCertification: boolean }[],
    rush: false, sameDay: false,
    shippingMethod: 'standard', shippingAddress: '', shippingCity: '', shippingState: '', shippingZip: '',
  });

  // Pricing calculator state
  const [calcDocType, setCalcDocType] = useState('State Apostille');
  const [calcState, setCalcState] = useState('DC');
  const [calcNeedNotary, setCalcNeedNotary] = useState(false);
  const [calcRush, setCalcRush] = useState(false);

  // Fetch orders from API
  useEffect(() => {
    setLoading(true);
    setOrdersError(null);
    fetch(`${API}/apostapp/orders`)
      .then(r => r.ok ? r.json() : Promise.reject(new Error('Failed to fetch orders')))
      .then(data => {
        const orderList = (Array.isArray(data) ? data : (data.orders || [])).map((o: any) => ({
          ...o,
          orderNumber: o.order_number || o.orderNumber || o.id,
          createdAt: o.created_at || o.createdAt,
          sameDay: o.same_day ?? o.sameDay ?? false,
          paid: o.paid ?? false,
          shippingMethod: o.shipping_method || o.shippingMethod,
          shippingAddress: o.shipping_address || o.shippingAddress,
          customer: {
            name: o.customer_name || o.customer?.name || '',
            email: o.customer_email || o.customer?.email || '',
            phone: o.customer_phone || o.customer?.phone || '',
          },
          documents: (o.documents || []).map((d: any) => ({
            id: d.id || '',
            type: d.doc_type || d.type || 'other',
            description: d.doc_description || d.description || '',
            stateOfOrigin: d.state_of_origin || d.stateOfOrigin || 'DC',
            destinationCountry: d.destination_country || d.destinationCountry || '',
            needsNotarization: d.needs_notarization ?? d.needsNotarization ?? false,
            needsCertification: d.needs_certification ?? d.needsCertification ?? false,
            status: d.status || 'received',
            trackingNumber: d.tracking_number || d.trackingNumber,
          })),
          attachments: (o.attachments || []).map((a: any) => ({
            id: a.id || '',
            filename: a.filename || a.stored_as || '',
            stored_as: a.stored_as || '',
            content_type: a.content_type || '',
            size: a.size || 0,
            uploaded_at: a.uploaded_at || '',
          })),
        }));
        setOrders(orderList);
        const customerMap = new Map<string, ApostCustomer>();
        orderList.forEach((o: any) => {
          const cName = o.customer.name;
          const cEmail = o.customer.email;
          const cPhone = o.customer.phone;
          const key = cEmail || cName;
          if (customerMap.has(key)) {
            const existing = customerMap.get(key)!;
            existing.totalOrders += 1;
            existing.totalSpent += o.total || 0;
          } else {
            customerMap.set(key, {
              id: o.customer_id || `c-${customerMap.size + 1}`,
              name: cName,
              email: cEmail,
              phone: cPhone,
              totalOrders: 1,
              totalSpent: o.total || 0,
              orders: [],
            });
          }
        });
        setCustomers(Array.from(customerMap.values()));
      })
      .catch((err) => { setOrdersError(err.message || 'Failed to load orders'); })
      .finally(() => setLoading(false));
  }, []);

  // ============ COMPUTED ============

  const activeOrders = orders.filter(o => !['completed', 'shipped'].includes(o.status)).length;
  const monthStart = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0, 10);
  const revenueMTD = orders.filter(o => (o.createdAt || '') >= monthStart).reduce((s, o) => s + (o.total || 0), 0);
  const atState = orders.filter(o => o.status === 'at_state').length;
  const completedThisMonth = orders.filter(o => o.status === 'completed' && (o.createdAt || '') >= monthStart).length;

  const filteredOrders = orderFilter === 'all' ? orders : orders.filter(o => o.status === orderFilter);

  const filteredCustomers = customerSearch
    ? customers.filter(c => c.name.toLowerCase().includes(customerSearch.toLowerCase()) || c.email.toLowerCase().includes(customerSearch.toLowerCase()))
    : customers;

  const docTypeCounts = orders.reduce<Record<string, number>>((acc, o) => {
    o.documents.forEach(d => { acc[d.type] = (acc[d.type] || 0) + 1; });
    return acc;
  }, {});
  const topDocTypes = Object.entries(docTypeCounts).sort((a, b) => b[1] - a[1]).slice(0, 5);
  const maxDocCount = topDocTypes.length > 0 ? topDocTypes[0][1] : 1;

  // Price calculator
  const calcService = PRICING_TABLE.find(p => p.service === calcDocType);
  const calcStateFee = calcService?.stateFees[calcState as keyof typeof calcService.stateFees] ?? 0;
  const calcTotal = (calcService?.baseFee || 0) + calcStateFee + (calcNeedNotary ? 25 : 0) + (calcRush ? 50 : 0);

  // New order running total
  const newOrderTotal = (() => {
    let total = 0;
    newOrder.documents.forEach(d => {
      total += 75; // base apostille fee
      if (d.needsNotarization) total += 25;
      if (d.needsCertification) total += 39;
    });
    if (newOrder.rush) total += 50;
    if (newOrder.sameDay) total += 100;
    const ship = SHIPPING_METHODS.find(s => s.id === newOrder.shippingMethod);
    if (ship) total += ship.fee;
    return total;
  })();

  // ============ HANDLERS ============

  const addDocumentToOrder = () => {
    setNewOrder(prev => ({
      ...prev,
      documents: [...prev.documents, { type: DOC_TYPES[0], description: '', stateOfOrigin: 'DC', destinationCountry: '', needsNotarization: false, needsCertification: false }],
    }));
  };

  const removeDocumentFromOrder = (idx: number) => {
    setNewOrder(prev => ({ ...prev, documents: prev.documents.filter((_, i) => i !== idx) }));
  };

  const updateDocument = (idx: number, field: string, value: any) => {
    setNewOrder(prev => ({
      ...prev,
      documents: prev.documents.map((d, i) => i === idx ? { ...d, [field]: value } : d),
    }));
  };

  const submitOrder = async () => {
    try {
      setSubmitting(true);
      const shippingParts = [newOrder.shippingAddress, newOrder.shippingCity, newOrder.shippingState, newOrder.shippingZip].filter(Boolean);
      const payload = {
        customer_name: newOrder.customerName,
        customer_email: newOrder.customerEmail || null,
        customer_phone: newOrder.customerPhone || null,
        documents: newOrder.documents.map(d => ({
          doc_type: d.type,
          doc_description: d.description,
          state_of_origin: d.stateOfOrigin,
          destination_country: d.destinationCountry,
          needs_notarization: d.needsNotarization,
          needs_certification: d.needsCertification,
        })),
        rush: newOrder.rush,
        same_day: newOrder.sameDay,
        shipping_method: newOrder.shippingMethod,
        shipping_address: shippingParts.join(', ') || null,
      };
      const res = await fetch(`${API}/apostapp/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        const created = await res.json();
        setOrders(prev => [created, ...prev]);
        setActiveSection('orders');
        setNewOrder({ customerName: '', customerEmail: '', customerPhone: '', documents: [], rush: false, sameDay: false, shippingMethod: 'standard', shippingAddress: '', shippingCity: '', shippingState: '', shippingZip: '' });
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`Failed to submit order: ${err.detail || res.statusText}`);
      }
    } catch {
      alert('Failed to submit order. Please check your connection and try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleTrackingSearch = () => {
    const found = orders.find(o =>
      o.orderNumber.toLowerCase() === trackingQuery.toLowerCase() ||
      o.customer.email.toLowerCase() === trackingQuery.toLowerCase()
    );
    setTrackingResult(found || null);
  };

  const markOrderPaid = async (orderId: string) => {
    try {
      const res = await fetch(`${API}/apostapp/orders/${orderId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paid: true }),
      });
      if (res.ok) {
        setOrders(prev => prev.map(o => o.id === orderId ? { ...o, paid: true } : o));
      }
    } catch { /* ignore */ }
  };

  const updateOrderStatus = async (orderId: string, status: string) => {
    try {
      const res = await fetch(`${API}/apostapp/orders/${orderId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      if (res.ok) {
        setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status: status as any } : o));
      }
    } catch { /* ignore */ }
  };

  const uploadDocument = async (orderId: string, file: File) => {
    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch(`${API}/apostapp/orders/${orderId}/documents`, {
        method: 'POST',
        body: form,
      });
      if (res.ok) {
        const { attachment } = await res.json();
        setOrders(prev => prev.map(o => {
          if (o.id !== orderId) return o;
          return { ...o, attachments: [...(o.attachments || []), attachment] };
        }));
      }
    } catch { /* ignore */ }
  };

  const importFromLLC = async (llcId: string) => {
    try {
      const res = await fetch(`${API}/apostapp/orders/from-llc/${llcId}`, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
      if (res.ok) {
        const created = await res.json();
        setOrders(prev => [created, ...prev]);
      }
    } catch {
      // API not available
    }
  };

  // ============ SUB-COMPONENTS ============

  const StatusBadge = ({ status }: { status: string }) => {
    const s = STATUS_COLORS[status] || STATUS_COLORS.received;
    return (
      <span style={{ background: s.bg, color: s.color, padding: '2px 10px', borderRadius: 999, fontSize: 11, fontWeight: 600 }}>
        {s.label}
      </span>
    );
  };

  const KPICard = ({ label, value, icon: Icon, color }: { label: string; value: string | number; icon: any; color: string }) => (
    <div className="empire-card" style={{ padding: 20, display: 'flex', alignItems: 'center', gap: 16 }}>
      <div style={{ width: 44, height: 44, borderRadius: 10, background: `${color}18`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Icon size={22} style={{ color }} />
      </div>
      <div>
        <div style={{ fontSize: 24, fontWeight: 700, color: '#1a1a1a' }}>{value}</div>
        <div style={{ fontSize: 12, color: '#6b7280' }}>{label}</div>
      </div>
    </div>
  );

  // ============ SECTIONS ============

  const renderOverview = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {ordersError && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8 }}>
          <AlertTriangle size={16} style={{ color: '#dc2626' }} />
          <span style={{ fontSize: 13, color: '#dc2626' }}>{ordersError}. Showing empty state — connect backend to see live data.</span>
        </div>
      )}
      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
        <KPICard label="Active Orders" value={activeOrders} icon={FileText} color="#2563eb" />
        <KPICard label="Revenue MTD" value={`$${revenueMTD.toLocaleString()}`} icon={DollarSign} color="#16a34a" />
        <KPICard label="At State" value={atState} icon={Building} color="#b8960c" />
        <KPICard label="Completed This Month" value={completedThisMonth} icon={CheckCircle} color="#7c3aed" />
      </div>

      {/* Quick Actions */}
      <div className="empire-card" style={{ padding: 20 }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Quick Actions</div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button onClick={() => setActiveSection('new-order')} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 20px', background: '#b8960c', color: '#fff', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 13 }}>
            <Plus size={16} /> New Order
          </button>
          <button onClick={() => setActiveSection('pricing')} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 20px', background: '#fdf8eb', color: '#b8960c', borderRadius: 8, border: '1px solid #ece8e0', cursor: 'pointer', fontWeight: 600, fontSize: 13 }}>
            <DollarSign size={16} /> Pricing Calculator
          </button>
          <button onClick={() => setActiveSection('tracking')} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 20px', background: '#fdf8eb', color: '#b8960c', borderRadius: 8, border: '1px solid #ece8e0', cursor: 'pointer', fontWeight: 600, fontSize: 13 }}>
            <Search size={16} /> Track Order
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Recent Orders */}
        <div className="empire-card" style={{ padding: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Recent Orders</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {orders.slice(0, 5).map(o => (
              <div key={o.id} onClick={() => { setActiveSection('orders'); setExpandedOrder(o.id); }}
                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', borderRadius: 8, background: '#faf9f7', cursor: 'pointer', border: '1px solid #ece8e0' }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{o.orderNumber}</div>
                  <div style={{ fontSize: 11, color: '#6b7280' }}>{o.customer.name} — {o.documents.length} doc{o.documents.length > 1 ? 's' : ''}</div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {o.rush && <span style={{ background: '#fef3c7', color: '#d97706', padding: '2px 8px', borderRadius: 999, fontSize: 10, fontWeight: 700 }}>RUSH</span>}
                  <StatusBadge status={o.status} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Top Document Types */}
        <div className="empire-card" style={{ padding: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Top Document Types</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {topDocTypes.map(([type, count]) => (
              <div key={type}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                  <span style={{ fontWeight: 500 }}>{type}</span>
                  <span style={{ color: '#6b7280' }}>{count}</span>
                </div>
                <div style={{ height: 8, background: '#ece8e0', borderRadius: 4, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${(count / maxDocCount) * 100}%`, background: '#b8960c', borderRadius: 4, transition: 'width 0.3s' }} />
                </div>
              </div>
            ))}
            {topDocTypes.length === 0 && <div style={{ fontSize: 12, color: '#6b7280' }}>No documents yet</div>}
          </div>
        </div>
      </div>
    </div>
  );

  const renderOrders = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        {[{ key: 'all', label: 'All' }, { key: 'received', label: 'Received' }, { key: 'processing', label: 'Processing' }, { key: 'at_state', label: 'At State' }, { key: 'completed', label: 'Completed' }, { key: 'shipped', label: 'Shipped' }].map(f => (
          <button key={f.key} onClick={() => setOrderFilter(f.key)}
            style={{ padding: '6px 16px', borderRadius: 999, border: '1px solid #ece8e0', background: orderFilter === f.key ? '#b8960c' : '#faf9f7', color: orderFilter === f.key ? '#fff' : '#1a1a1a', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
            {f.label}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <button onClick={() => setActiveSection('new-order')}
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', background: '#b8960c', color: '#fff', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 13 }}>
          <Plus size={14} /> New Order
        </button>
      </div>

      {/* Orders Table */}
      <div className="empire-card" style={{ overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#faf9f7', borderBottom: '1px solid #ece8e0' }}>
              <th style={{ textAlign: 'left', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Order #</th>
              <th style={{ textAlign: 'left', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Customer</th>
              <th style={{ textAlign: 'center', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Docs</th>
              <th style={{ textAlign: 'center', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Status</th>
              <th style={{ textAlign: 'center', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Paid</th>
              <th style={{ textAlign: 'center', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Rush</th>
              <th style={{ textAlign: 'right', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Total</th>
              <th style={{ textAlign: 'right', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Date</th>
              <th style={{ width: 30 }} />
            </tr>
          </thead>
          <tbody>
            {filteredOrders.map(o => (
              <React.Fragment key={o.id}>
                <tr onClick={() => setExpandedOrder(expandedOrder === o.id ? null : o.id)}
                  style={{ borderBottom: '1px solid #ece8e0', cursor: 'pointer', background: expandedOrder === o.id ? '#fdf8eb' : undefined }}>
                  <td style={{ padding: '12px 14px', fontWeight: 600 }}>{o.orderNumber}</td>
                  <td style={{ padding: '12px 14px' }}>{o.customer.name}</td>
                  <td style={{ padding: '12px 14px', textAlign: 'center' }}>{o.documents.length}</td>
                  <td style={{ padding: '12px 14px', textAlign: 'center' }}><StatusBadge status={o.status} /></td>
                  <td style={{ padding: '12px 14px', textAlign: 'center' }}>
                    {o.paid
                      ? <span style={{ background: '#dcfce7', color: '#16a34a', padding: '2px 8px', borderRadius: 999, fontSize: 10, fontWeight: 700 }}>PAID</span>
                      : <span style={{ background: '#fef2f2', color: '#dc2626', padding: '2px 8px', borderRadius: 999, fontSize: 10, fontWeight: 700 }}>UNPAID</span>}
                  </td>
                  <td style={{ padding: '12px 14px', textAlign: 'center' }}>
                    {o.rush && <span style={{ background: '#fef3c7', color: '#d97706', padding: '2px 8px', borderRadius: 999, fontSize: 10, fontWeight: 700 }}>RUSH</span>}
                    {o.sameDay && <span style={{ background: '#fee2e2', color: '#dc2626', padding: '2px 8px', borderRadius: 999, fontSize: 10, fontWeight: 700, marginLeft: 4 }}>SAME-DAY</span>}
                  </td>
                  <td style={{ padding: '12px 14px', textAlign: 'right', fontWeight: 600 }}>${o.total}</td>
                  <td style={{ padding: '12px 14px', textAlign: 'right', color: '#6b7280' }}>{o.createdAt}</td>
                  <td style={{ padding: '12px 14px' }}>
                    {expandedOrder === o.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </td>
                </tr>
                {expandedOrder === o.id && (
                  <tr>
                    <td colSpan={8} style={{ padding: '0 14px 14px' }}>
                      <div style={{ background: '#faf9f7', borderRadius: 8, padding: 16, marginTop: 4 }}>
                        <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 10 }}>Documents in Order</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                          {o.documents.map(d => (
                            <div key={d.id} style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '10px 12px', background: '#fff', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 12 }}>
                              <div style={{ flex: 1 }}>
                                <div style={{ fontWeight: 600 }}>{d.type}</div>
                                <div style={{ color: '#6b7280', fontSize: 11 }}>{d.description}</div>
                              </div>
                              <div style={{ color: '#6b7280' }}>{d.stateOfOrigin}</div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}><Globe size={12} style={{ color: '#6b7280' }} /> {d.destinationCountry}</div>
                              {d.needsNotarization && <span style={{ background: '#dbeafe', color: '#2563eb', padding: '2px 8px', borderRadius: 999, fontSize: 10, fontWeight: 600 }}>Notary</span>}
                              <StatusBadge status={d.status} />
                              {d.trackingNumber && <span style={{ fontSize: 10, color: '#6b7280' }}>#{d.trackingNumber}</span>}
                            </div>
                          ))}
                        </div>

                        {/* Admin Controls */}
                        <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #e5e7eb', display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <label style={{ fontSize: 11, fontWeight: 600, color: '#6b7280' }}>Status:</label>
                            <select value={o.status} onChange={e => updateOrderStatus(o.id, e.target.value)}
                              style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid #d1d5db', fontSize: 12 }}>
                              <option value="received">Received</option>
                              <option value="processing">Processing</option>
                              <option value="at_state">At State</option>
                              <option value="completed">Completed</option>
                              <option value="shipped">Shipped</option>
                            </select>
                          </div>
                          {!o.paid && (
                            <button onClick={() => markOrderPaid(o.id)}
                              style={{ padding: '4px 12px', background: '#16a34a', color: '#fff', borderRadius: 6, border: 'none', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                              Mark Paid
                            </button>
                          )}
                          {o.paid && <span style={{ fontSize: 11, fontWeight: 700, color: '#16a34a' }}>✓ Paid</span>}
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 'auto' }}>
                            <input type="file" id={`upload-${o.id}`} accept=".pdf,.jpg,.jpeg,.png,.gif,.webp"
                              onChange={e => { const f = (e.target as HTMLInputElement).files?.[0]; if (f) uploadDocument(o.id, f); e.target.value = ''; }}
                              style={{ fontSize: 11 }} />
                          </div>
                        </div>

                        {/* Attachments */}
                        {o.attachments && o.attachments.length > 0 && (
                          <div style={{ marginTop: 12 }}>
                            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Uploaded Files</div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                              {o.attachments.map((a: Attachment) => (
                                <div key={a.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, padding: '6px 10px', background: '#fff', borderRadius: 6, border: '1px solid #e5e7eb' }}>
                                  <FileText size={12} style={{ color: '#6b7280' }} />
                                  <span style={{ flex: 1 }}>{a.filename}</span>
                                  <span style={{ color: '#6b7280', fontSize: 10 }}>{(a.size / 1024).toFixed(1)}KB</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
        {filteredOrders.length === 0 && (
          <div style={{ padding: 40, textAlign: 'center', color: '#6b7280', fontSize: 13 }}>No orders found</div>
        )}
      </div>
    </div>
  );

  const renderNewOrder = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Customer Info */}
      <div className="empire-card" style={{ padding: 20 }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <User size={16} style={{ color: '#b8960c' }} /> Customer Information
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
          <div>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', display: 'block', marginBottom: 4 }}>Full Name</label>
            <input value={newOrder.customerName} onChange={e => setNewOrder(p => ({ ...p, customerName: e.target.value }))}
              placeholder="John Doe" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#faf9f7', outline: 'none' }} />
          </div>
          <div>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', display: 'block', marginBottom: 4 }}>Email</label>
            <input value={newOrder.customerEmail} onChange={e => setNewOrder(p => ({ ...p, customerEmail: e.target.value }))}
              placeholder="john@example.com" type="email" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#faf9f7', outline: 'none' }} />
          </div>
          <div>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', display: 'block', marginBottom: 4 }}>Phone</label>
            <input value={newOrder.customerPhone} onChange={e => setNewOrder(p => ({ ...p, customerPhone: e.target.value }))}
              placeholder="202-555-0100" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#faf9f7', outline: 'none' }} />
          </div>
        </div>
      </div>

      {/* Documents */}
      <div className="empire-card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <div style={{ fontSize: 14, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
            <FileText size={16} style={{ color: '#b8960c' }} /> Documents
          </div>
          <button onClick={addDocumentToOrder}
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', background: '#b8960c', color: '#fff', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 12 }}>
            <Plus size={14} /> Add Document
          </button>
        </div>
        {newOrder.documents.length === 0 && (
          <div style={{ padding: 30, textAlign: 'center', color: '#6b7280', fontSize: 13, border: '2px dashed #ece8e0', borderRadius: 8 }}>
            Click "Add Document" to add documents to this order
          </div>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {newOrder.documents.map((d, i) => (
            <div key={i} style={{ padding: 14, borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <div style={{ fontSize: 12, fontWeight: 600 }}>Document #{i + 1}</div>
                <button onClick={() => removeDocumentFromOrder(i)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444' }}><X size={16} /></button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', display: 'block', marginBottom: 4 }}>Document Type</label>
                  <select value={d.type} onChange={e => updateDocument(i, 'type', e.target.value)}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#fff', outline: 'none' }}>
                    {DOC_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', display: 'block', marginBottom: 4 }}>Description</label>
                  <input value={d.description} onChange={e => updateDocument(i, 'description', e.target.value)}
                    placeholder="Purpose / details" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#fff', outline: 'none' }} />
                </div>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', display: 'block', marginBottom: 4 }}>State of Origin</label>
                  <select value={d.stateOfOrigin} onChange={e => updateDocument(i, 'stateOfOrigin', e.target.value)}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#fff', outline: 'none' }}>
                    {US_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', display: 'block', marginBottom: 4 }}>Destination Country</label>
                  <input value={d.destinationCountry} onChange={e => updateDocument(i, 'destinationCountry', e.target.value)}
                    placeholder="e.g. Spain, Germany" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#fff', outline: 'none' }} />
                </div>
              </div>
              <div style={{ display: 'flex', gap: 20, marginTop: 10 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
                  <input type="checkbox" checked={d.needsNotarization} onChange={e => updateDocument(i, 'needsNotarization', e.target.checked)} />
                  Needs Notarization (+$25)
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
                  <input type="checkbox" checked={d.needsCertification} onChange={e => updateDocument(i, 'needsCertification', e.target.checked)} />
                  Needs Certification (+$39)
                </label>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Service Options */}
      <div className="empire-card" style={{ padding: 20 }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Zap size={16} style={{ color: '#b8960c' }} /> Service Options
        </div>
        <div style={{ display: 'flex', gap: 20 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer', padding: '10px 16px', borderRadius: 8, border: `1px solid ${newOrder.rush ? '#b8960c' : '#ece8e0'}`, background: newOrder.rush ? '#fdf8eb' : '#fff' }}>
            <input type="checkbox" checked={newOrder.rush} onChange={e => setNewOrder(p => ({ ...p, rush: e.target.checked }))} />
            <Zap size={14} style={{ color: '#d97706' }} /> Rush Processing (+$50)
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer', padding: '10px 16px', borderRadius: 8, border: `1px solid ${newOrder.sameDay ? '#b8960c' : '#ece8e0'}`, background: newOrder.sameDay ? '#fdf8eb' : '#fff' }}>
            <input type="checkbox" checked={newOrder.sameDay} onChange={e => setNewOrder(p => ({ ...p, sameDay: e.target.checked }))} />
            <Clock size={14} style={{ color: '#dc2626' }} /> Same-Day Processing — DC only (+$100)
          </label>
        </div>
      </div>

      {/* Shipping */}
      <div className="empire-card" style={{ padding: 20 }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Truck size={16} style={{ color: '#b8960c' }} /> Shipping
        </div>
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', display: 'block', marginBottom: 4 }}>Shipping Method</label>
          <select value={newOrder.shippingMethod} onChange={e => setNewOrder(p => ({ ...p, shippingMethod: e.target.value }))}
            style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#faf9f7', outline: 'none' }}>
            {SHIPPING_METHODS.map(m => <option key={m.id} value={m.id}>{m.label} {m.fee > 0 ? `($${m.fee})` : '(Free)'}</option>)}
          </select>
        </div>
        {newOrder.shippingMethod !== 'pickup' && (
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: 10 }}>
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', display: 'block', marginBottom: 4 }}>Address</label>
              <input value={newOrder.shippingAddress} onChange={e => setNewOrder(p => ({ ...p, shippingAddress: e.target.value }))}
                placeholder="123 Main St" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#faf9f7', outline: 'none' }} />
            </div>
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', display: 'block', marginBottom: 4 }}>City</label>
              <input value={newOrder.shippingCity} onChange={e => setNewOrder(p => ({ ...p, shippingCity: e.target.value }))}
                placeholder="Washington" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#faf9f7', outline: 'none' }} />
            </div>
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', display: 'block', marginBottom: 4 }}>State</label>
              <select value={newOrder.shippingState} onChange={e => setNewOrder(p => ({ ...p, shippingState: e.target.value }))}
                style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#faf9f7', outline: 'none' }}>
                <option value="">--</option>
                {US_STATES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', display: 'block', marginBottom: 4 }}>ZIP</label>
              <input value={newOrder.shippingZip} onChange={e => setNewOrder(p => ({ ...p, shippingZip: e.target.value }))}
                placeholder="20001" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#faf9f7', outline: 'none' }} />
            </div>
          </div>
        )}
      </div>

      {/* Running Total + Submit */}
      <div className="empire-card" style={{ padding: 20, background: '#fdf8eb', border: '2px solid #b8960c' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>Order Total</div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>
              {newOrder.documents.length} document{newOrder.documents.length !== 1 ? 's' : ''}
              {newOrder.rush ? ' + Rush' : ''}
              {newOrder.sameDay ? ' + Same-Day' : ''}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#b8960c' }}>${newOrderTotal}</div>
            <button onClick={submitOrder} disabled={submitting || !newOrder.customerName || newOrder.documents.length === 0}
              style={{ padding: '12px 28px', background: !submitting && newOrder.customerName && newOrder.documents.length > 0 ? '#b8960c' : '#d1d5db', color: '#fff', borderRadius: 8, border: 'none', cursor: !submitting && newOrder.customerName && newOrder.documents.length > 0 ? 'pointer' : 'not-allowed', fontWeight: 700, fontSize: 14 }}>
              {submitting ? 'Submitting...' : 'Submit Order'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  const renderCustomers = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#6b7280' }} />
          <input value={customerSearch} onChange={e => { setCustomerSearch(e.target.value); setSelectedCustomer(null); }}
            placeholder="Search customers by name or email..."
            style={{ width: '100%', padding: '10px 12px 10px 34px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#faf9f7', outline: 'none' }} />
        </div>
      </div>

      {selectedCustomer ? (
        <div className="empire-card" style={{ padding: 20 }}>
          <button onClick={() => setSelectedCustomer(null)} style={{ fontSize: 12, color: '#b8960c', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600, marginBottom: 12 }}>
            ← Back to list
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20 }}>
            <div style={{ width: 48, height: 48, borderRadius: '50%', background: '#b8960c18', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <User size={24} style={{ color: '#b8960c' }} />
            </div>
            <div>
              <div style={{ fontSize: 18, fontWeight: 700 }}>{selectedCustomer.name}</div>
              <div style={{ fontSize: 12, color: '#6b7280' }}>{selectedCustomer.email} — {selectedCustomer.phone}</div>
            </div>
            <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#16a34a' }}>${selectedCustomer.totalSpent}</div>
              <div style={{ fontSize: 11, color: '#6b7280' }}>{selectedCustomer.totalOrders} orders</div>
            </div>
          </div>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>Order History</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {orders.filter(o => o.customer.email === selectedCustomer.email).map(o => (
              <div key={o.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', borderRadius: 8, background: '#faf9f7', border: '1px solid #ece8e0' }}>
                <div>
                  <span style={{ fontWeight: 600, fontSize: 13 }}>{o.orderNumber}</span>
                  <span style={{ fontSize: 11, color: '#6b7280', marginLeft: 8 }}>{o.documents.length} doc{o.documents.length > 1 ? 's' : ''}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <StatusBadge status={o.status} />
                  <span style={{ fontWeight: 600, fontSize: 13 }}>${o.total}</span>
                  <span style={{ fontSize: 11, color: '#6b7280' }}>{o.createdAt}</span>
                </div>
              </div>
            ))}
            {orders.filter(o => o.customer.email === selectedCustomer.email).length === 0 && (
              <div style={{ padding: 20, textAlign: 'center', color: '#6b7280', fontSize: 12 }}>No orders found for this customer</div>
            )}
          </div>
        </div>
      ) : (
        <div className="empire-card" style={{ overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#faf9f7', borderBottom: '1px solid #ece8e0' }}>
                <th style={{ textAlign: 'left', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Name</th>
                <th style={{ textAlign: 'left', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Email</th>
                <th style={{ textAlign: 'left', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Phone</th>
                <th style={{ textAlign: 'center', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Orders</th>
                <th style={{ textAlign: 'right', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Total Spent</th>
              </tr>
            </thead>
            <tbody>
              {filteredCustomers.map(c => (
                <tr key={c.id} onClick={() => setSelectedCustomer(c)}
                  style={{ borderBottom: '1px solid #ece8e0', cursor: 'pointer' }}
                  onMouseOver={e => (e.currentTarget.style.background = '#fdf8eb')}
                  onMouseOut={e => (e.currentTarget.style.background = '')}>
                  <td style={{ padding: '12px 14px', fontWeight: 600 }}>{c.name}</td>
                  <td style={{ padding: '12px 14px', color: '#6b7280' }}>{c.email}</td>
                  <td style={{ padding: '12px 14px', color: '#6b7280' }}>{c.phone}</td>
                  <td style={{ padding: '12px 14px', textAlign: 'center' }}>{c.totalOrders}</td>
                  <td style={{ padding: '12px 14px', textAlign: 'right', fontWeight: 600, color: '#16a34a' }}>${c.totalSpent}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredCustomers.length === 0 && (
            <div style={{ padding: 40, textAlign: 'center', color: '#6b7280', fontSize: 13 }}>No customers found</div>
          )}
        </div>
      )}
    </div>
  );

  const renderPricing = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Pricing Table */}
      <div className="empire-card" style={{ overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #ece8e0' }}>
          <div style={{ fontSize: 14, fontWeight: 600 }}>Full Service Pricing</div>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#faf9f7', borderBottom: '1px solid #ece8e0' }}>
              <th style={{ textAlign: 'left', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Service</th>
              <th style={{ textAlign: 'right', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Our Fee</th>
              <th style={{ textAlign: 'right', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>DC State Fee</th>
              <th style={{ textAlign: 'right', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>MD State Fee</th>
              <th style={{ textAlign: 'right', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>VA State Fee</th>
              <th style={{ textAlign: 'right', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Processing Time</th>
            </tr>
          </thead>
          <tbody>
            {PRICING_TABLE.map((p, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #ece8e0' }}>
                <td style={{ padding: '12px 14px', fontWeight: 600 }}>{p.service}</td>
                <td style={{ padding: '12px 14px', textAlign: 'right' }}>${p.baseFee}</td>
                <td style={{ padding: '12px 14px', textAlign: 'right', color: '#6b7280' }}>{p.stateFees.DC > 0 ? `$${p.stateFees.DC}` : '—'}</td>
                <td style={{ padding: '12px 14px', textAlign: 'right', color: '#6b7280' }}>{p.stateFees.MD > 0 ? `$${p.stateFees.MD}` : '—'}</td>
                <td style={{ padding: '12px 14px', textAlign: 'right', color: '#6b7280' }}>{p.stateFees.VA > 0 ? `$${p.stateFees.VA}` : '—'}</td>
                <td style={{ padding: '12px 14px', textAlign: 'right', color: '#6b7280' }}>{p.time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Shipping Fees */}
      <div className="empire-card" style={{ padding: 20 }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Shipping Options</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
          {SHIPPING_METHODS.map(m => (
            <div key={m.id} style={{ padding: 14, borderRadius: 8, background: '#faf9f7', border: '1px solid #ece8e0', textAlign: 'center' }}>
              <Truck size={18} style={{ color: '#b8960c', marginBottom: 6 }} />
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>{m.label.split('(')[0].trim()}</div>
              <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 4 }}>{m.label.match(/\(([^)]+)\)/)?.[1] || ''}</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: m.fee > 0 ? '#b8960c' : '#16a34a' }}>{m.fee > 0 ? `$${m.fee}` : 'Free'}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Interactive Calculator */}
      <div className="empire-card" style={{ padding: 20, background: '#fdf8eb', border: '2px solid #b8960c' }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <DollarSign size={16} style={{ color: '#b8960c' }} /> Pricing Calculator
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 12, marginBottom: 16 }}>
          <div>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', display: 'block', marginBottom: 4 }}>Service Type</label>
            <select value={calcDocType} onChange={e => setCalcDocType(e.target.value)}
              style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#fff', outline: 'none' }}>
              {PRICING_TABLE.filter(p => !['Rush Processing (+)', 'Same-Day (DC only)'].includes(p.service)).map(p => (
                <option key={p.service} value={p.service}>{p.service}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', display: 'block', marginBottom: 4 }}>State</label>
            <select value={calcState} onChange={e => setCalcState(e.target.value)}
              style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#fff', outline: 'none' }}>
              <option value="DC">DC</option>
              <option value="MD">MD</option>
              <option value="VA">VA</option>
            </select>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
              <input type="checkbox" checked={calcNeedNotary} onChange={e => setCalcNeedNotary(e.target.checked)} />
              + Notarization ($25)
            </label>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
              <input type="checkbox" checked={calcRush} onChange={e => setCalcRush(e.target.checked)} />
              + Rush Processing ($50)
            </label>
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 18px', background: '#fff', borderRadius: 8 }}>
          <div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>
              Service: ${calcService?.baseFee || 0} + State Fee: ${calcStateFee}
              {calcNeedNotary ? ' + Notary: $25' : ''}
              {calcRush ? ' + Rush: $50' : ''}
            </div>
            <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>Est. processing: {calcService?.time || 'N/A'}</div>
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#b8960c' }}>${calcTotal}</div>
        </div>
      </div>
    </div>
  );

  const renderLLCIntegration = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="empire-card" style={{ padding: 20 }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Building size={16} style={{ color: '#b8960c' }} /> LLC Factory Integration
        </div>
        <p style={{ fontSize: 13, color: '#6b7280', marginBottom: 16 }}>
          Import completed LLC Factory orders that need document apostille. One-click to create an apostille order from any LLC order.
        </p>
      </div>

      <div className="empire-card" style={{ overflow: 'hidden' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid #ece8e0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>Available LLC Orders</div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {llcOrders.map(llc => (
            <div key={llc.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 20px', borderBottom: '1px solid #ece8e0' }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{llc.company}</div>
                <div style={{ fontSize: 11, color: '#6b7280' }}>State: {llc.state} — {llc.documents.length} document{llc.documents.length > 1 ? 's' : ''}</div>
                <div style={{ display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
                  {llc.documents.map((d, i) => (
                    <span key={i} style={{ background: '#f3f4f6', padding: '2px 10px', borderRadius: 999, fontSize: 11, color: '#374151' }}>{d}</span>
                  ))}
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <StatusBadge status={llc.status} />
                <button onClick={() => importFromLLC(llc.id)}
                  style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', background: '#b8960c', color: '#fff', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 12, whiteSpace: 'nowrap' }}>
                  <Plus size={14} /> Create Apostille Order
                </button>
              </div>
            </div>
          ))}
          {llcOrders.length === 0 && (
            <div style={{ padding: 40, textAlign: 'center', color: '#6b7280', fontSize: 13 }}>No LLC orders available for import</div>
          )}
        </div>
      </div>
    </div>
  );

  const renderTracking = () => {
    const getStepIndex = (status: string) => TRACKING_STEPS.findIndex(s => s.key === status);

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Search */}
        <div className="empire-card" style={{ padding: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Track Your Order</div>
          <div style={{ display: 'flex', gap: 10 }}>
            <div style={{ flex: 1, position: 'relative' }}>
              <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#6b7280' }} />
              <input value={trackingQuery} onChange={e => setTrackingQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleTrackingSearch()}
                placeholder="Enter order number (e.g. APT-2026-001) or customer email"
                style={{ width: '100%', padding: '10px 12px 10px 34px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#faf9f7', outline: 'none' }} />
            </div>
            <button onClick={handleTrackingSearch}
              style={{ padding: '10px 20px', background: '#b8960c', color: '#fff', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 13 }}>
              Track
            </button>
          </div>
        </div>

        {trackingResult && (
          <div className="empire-card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div>
                <div style={{ fontSize: 18, fontWeight: 700 }}>{trackingResult.orderNumber}</div>
                <div style={{ fontSize: 12, color: '#6b7280' }}>{trackingResult.customer.name} — {trackingResult.createdAt}</div>
              </div>
              <StatusBadge status={trackingResult.status} />
            </div>

            {/* Document Timelines */}
            {trackingResult.documents.map(doc => {
              const currentStep = getStepIndex(doc.status);
              return (
                <div key={doc.id} style={{ marginBottom: 24, padding: 16, background: '#faf9f7', borderRadius: 8, border: '1px solid #ece8e0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 14 }}>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{doc.type}</div>
                      <div style={{ fontSize: 11, color: '#6b7280' }}>{doc.stateOfOrigin} → {doc.destinationCountry}</div>
                    </div>
                    {doc.trackingNumber && <span style={{ fontSize: 11, color: '#6b7280' }}>Tracking: {doc.trackingNumber}</span>}
                  </div>

                  {/* Timeline */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 0, position: 'relative' }}>
                    {TRACKING_STEPS.map((step, i) => {
                      const isActive = i <= currentStep;
                      const isCurrent = i === currentStep;
                      const StepIcon = step.icon;
                      return (
                        <React.Fragment key={step.key}>
                          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, position: 'relative', zIndex: 1 }}>
                            <div style={{
                              width: 36, height: 36, borderRadius: '50%',
                              background: isActive ? '#b8960c' : '#e5e7eb',
                              display: 'flex', alignItems: 'center', justifyContent: 'center',
                              border: isCurrent ? '3px solid #b8960c44' : 'none',
                              transition: 'all 0.3s',
                            }}>
                              <StepIcon size={16} style={{ color: isActive ? '#fff' : '#9ca3af' }} />
                            </div>
                            <div style={{ fontSize: 10, fontWeight: isActive ? 600 : 400, color: isActive ? '#b8960c' : '#9ca3af', marginTop: 6, textAlign: 'center' }}>
                              {step.label}
                            </div>
                          </div>
                          {i < TRACKING_STEPS.length - 1 && (
                            <div style={{ flex: 1, height: 3, background: i < currentStep ? '#b8960c' : '#e5e7eb', marginBottom: 20, borderRadius: 2 }} />
                          )}
                        </React.Fragment>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {trackingQuery && !trackingResult && (
          <div className="empire-card" style={{ padding: 40, textAlign: 'center' }}>
            <AlertTriangle size={32} style={{ color: '#d97706', marginBottom: 10 }} />
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>Order Not Found</div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>No order matches "{trackingQuery}". Check the order number or email and try again.</div>
          </div>
        )}
      </div>
    );
  };

  // ============ NEW SECTIONS ============

  const addIntakeDocument = () => {
    setIntakeForm(prev => ({
      ...prev,
      documents: [...prev.documents, { docType: DOC_TYPES[0], originalLanguage: 'English', destinationCountry: '', purpose: 'personal', copies: 1, needsNotarization: false, signerName: '', signerPresent: true }],
    }));
  };

  const removeIntakeDocument = (idx: number) => {
    setIntakeForm(prev => ({ ...prev, documents: prev.documents.filter((_, i) => i !== idx) }));
  };

  const updateIntakeDocument = (idx: number, field: string, value: any) => {
    setIntakeForm(prev => ({
      ...prev,
      documents: prev.documents.map((d, i) => i === idx ? { ...d, [field]: value } : d),
    }));
  };

  const saveClientProfile = () => {
    const client: IntakeClient = {
      ...intakeForm,
      id: `client-${Date.now()}`,
      createdAt: new Date().toISOString().split('T')[0],
    };
    const updated = [client, ...savedClients];
    setSavedClients(updated);
    try { localStorage.setItem('apostapp-intake-clients', JSON.stringify(updated)); } catch {}
    setActiveSection('customers');
  };

  const startOrderFromIntake = () => {
    setNewOrder(prev => ({
      ...prev,
      customerName: intakeForm.fullName,
      customerEmail: intakeForm.email,
      customerPhone: intakeForm.phone,
      shippingAddress: intakeForm.street,
      shippingCity: intakeForm.city,
      shippingState: intakeForm.state,
      shippingZip: intakeForm.zip,
      rush: intakeForm.urgency === 'rush',
      sameDay: intakeForm.urgency === 'same-day',
      documents: intakeForm.documents.map(d => ({
        type: d.docType, description: `For ${d.destinationCountry} - ${d.purpose}`,
        stateOfOrigin: intakeForm.state || 'DC', destinationCountry: d.destinationCountry,
        needsNotarization: d.needsNotarization, needsCertification: true,
      })),
    }));
    setActiveSection('new-order');
  };

  const inputStyle = { width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#faf9f7', outline: 'none' } as const;
  const labelStyle = { fontSize: 11, fontWeight: 600, color: '#6b7280', display: 'block', marginBottom: 4 } as const;

  const renderIntake = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Personal Information */}
      <div className="empire-card" style={{ padding: 20 }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <User size={16} style={{ color: '#b8960c' }} /> Personal Information
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
          <div>
            <label style={labelStyle}>Full Legal Name *</label>
            <input value={intakeForm.fullName} onChange={e => setIntakeForm(p => ({ ...p, fullName: e.target.value }))} placeholder="John Michael Doe" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Date of Birth</label>
            <input type="date" value={intakeForm.dateOfBirth} onChange={e => setIntakeForm(p => ({ ...p, dateOfBirth: e.target.value }))} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>SSN (Last 4)</label>
            <input value={intakeForm.ssnLast4} onChange={e => setIntakeForm(p => ({ ...p, ssnLast4: e.target.value.replace(/\D/g, '').slice(0, 4) }))} placeholder="1234" maxLength={4} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Nationality</label>
            <input value={intakeForm.nationality} onChange={e => setIntakeForm(p => ({ ...p, nationality: e.target.value }))} placeholder="US Citizen" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Gender</label>
            <select value={intakeForm.gender} onChange={e => setIntakeForm(p => ({ ...p, gender: e.target.value }))} style={inputStyle}>
              <option value="">Select...</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="non-binary">Non-Binary</option>
              <option value="prefer-not">Prefer not to say</option>
            </select>
          </div>
        </div>
      </div>

      {/* Contact Information */}
      <div className="empire-card" style={{ padding: 20 }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Mail size={16} style={{ color: '#b8960c' }} /> Contact Information
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div>
            <label style={labelStyle}>Email *</label>
            <input type="email" value={intakeForm.email} onChange={e => setIntakeForm(p => ({ ...p, email: e.target.value }))} placeholder="john@example.com" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Phone *</label>
            <input value={intakeForm.phone} onChange={e => setIntakeForm(p => ({ ...p, phone: e.target.value }))} placeholder="202-555-0100" style={inputStyle} />
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr', gap: 12, marginTop: 12 }}>
          <div>
            <label style={labelStyle}>Street Address</label>
            <input value={intakeForm.street} onChange={e => setIntakeForm(p => ({ ...p, street: e.target.value }))} placeholder="123 Main St" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>City</label>
            <input value={intakeForm.city} onChange={e => setIntakeForm(p => ({ ...p, city: e.target.value }))} placeholder="Washington" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>State</label>
            <select value={intakeForm.state} onChange={e => setIntakeForm(p => ({ ...p, state: e.target.value }))} style={inputStyle}>
              <option value="">--</option>
              {US_STATES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label style={labelStyle}>ZIP</label>
            <input value={intakeForm.zip} onChange={e => setIntakeForm(p => ({ ...p, zip: e.target.value }))} placeholder="20001" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Country</label>
            <input value={intakeForm.country} onChange={e => setIntakeForm(p => ({ ...p, country: e.target.value }))} placeholder="US" style={inputStyle} />
          </div>
        </div>
      </div>

      {/* Government ID */}
      <div className="empire-card" style={{ padding: 20 }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Shield size={16} style={{ color: '#b8960c' }} /> Government ID
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 12 }}>
          <div>
            <label style={labelStyle}>ID Type</label>
            <select value={intakeForm.idType} onChange={e => setIntakeForm(p => ({ ...p, idType: e.target.value }))} style={inputStyle}>
              <option value="passport">Passport</option>
              <option value="drivers-license">Driver&apos;s License</option>
              <option value="state-id">State ID</option>
            </select>
          </div>
          <div>
            <label style={labelStyle}>ID Number</label>
            <input value={intakeForm.idNumber} onChange={e => setIntakeForm(p => ({ ...p, idNumber: e.target.value }))} placeholder="ID Number" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Issue Date</label>
            <input type="date" value={intakeForm.idIssueDate} onChange={e => setIntakeForm(p => ({ ...p, idIssueDate: e.target.value }))} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Expiry Date</label>
            <input type="date" value={intakeForm.idExpiryDate} onChange={e => setIntakeForm(p => ({ ...p, idExpiryDate: e.target.value }))} style={inputStyle} />
          </div>
        </div>
        <div style={{ marginTop: 12 }}>
          <label style={labelStyle}>Issuing State/Country</label>
          <input value={intakeForm.idIssuingAuthority} onChange={e => setIntakeForm(p => ({ ...p, idIssuingAuthority: e.target.value }))} placeholder="e.g. DC, Maryland, US Dept of State" style={{ ...inputStyle, maxWidth: 400 }} />
        </div>
      </div>

      {/* Document Details */}
      <div className="empire-card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <div style={{ fontSize: 14, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
            <FileText size={16} style={{ color: '#b8960c' }} /> Document Details
          </div>
          <button onClick={addIntakeDocument}
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', background: '#b8960c', color: '#fff', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 12 }}>
            <Plus size={14} /> Add Document
          </button>
        </div>
        {intakeForm.documents.length === 0 && (
          <div style={{ padding: 30, textAlign: 'center', color: '#6b7280', fontSize: 13, border: '2px dashed #ece8e0', borderRadius: 8 }}>
            Click &quot;Add Document&quot; to add documents for apostille
          </div>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {intakeForm.documents.map((d, i) => (
            <div key={i} style={{ padding: 14, borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <div style={{ fontSize: 12, fontWeight: 600 }}>Document #{i + 1}</div>
                <button onClick={() => removeIntakeDocument(i)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444' }}><X size={16} /></button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                <div>
                  <label style={labelStyle}>Document Type</label>
                  <select value={d.docType} onChange={e => updateIntakeDocument(i, 'docType', e.target.value)} style={inputStyle}>
                    {DOC_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label style={labelStyle}>Original Language</label>
                  <input value={d.originalLanguage} onChange={e => updateIntakeDocument(i, 'originalLanguage', e.target.value)} style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Destination Country</label>
                  <input value={d.destinationCountry} onChange={e => updateIntakeDocument(i, 'destinationCountry', e.target.value)} placeholder="e.g. Spain" style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Purpose</label>
                  <select value={d.purpose} onChange={e => updateIntakeDocument(i, 'purpose', e.target.value)} style={inputStyle}>
                    <option value="employment">Employment</option>
                    <option value="education">Education</option>
                    <option value="legal">Legal</option>
                    <option value="personal">Personal</option>
                    <option value="immigration">Immigration</option>
                  </select>
                </div>
                <div>
                  <label style={labelStyle}>Number of Copies</label>
                  <input type="number" min={1} value={d.copies} onChange={e => updateIntakeDocument(i, 'copies', parseInt(e.target.value) || 1)} style={inputStyle} />
                </div>
              </div>
              <div style={{ display: 'flex', gap: 20, marginTop: 10, flexWrap: 'wrap' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
                  <input type="checkbox" checked={d.needsNotarization} onChange={e => updateIntakeDocument(i, 'needsNotarization', e.target.checked)} />
                  Needs Notarization
                </label>
                {d.needsNotarization && (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <label style={{ fontSize: 11, fontWeight: 600, color: '#6b7280' }}>Signer Name:</label>
                      <input value={d.signerName} onChange={e => updateIntakeDocument(i, 'signerName', e.target.value)} placeholder="Signer name" style={{ ...inputStyle, width: 180 }} />
                    </div>
                    <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
                      <input type="checkbox" checked={d.signerPresent} onChange={e => updateIntakeDocument(i, 'signerPresent', e.target.checked)} />
                      Signer Present?
                    </label>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Urgency, Payment, Referral */}
      <div className="empire-card" style={{ padding: 20 }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Clock size={16} style={{ color: '#b8960c' }} /> Urgency & Payment
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
          <div>
            <label style={labelStyle}>Urgency</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {(['standard', 'rush', 'same-day'] as const).map(u => (
                <label key={u} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer', padding: '8px 12px', borderRadius: 8, border: `1px solid ${intakeForm.urgency === u ? '#b8960c' : '#ece8e0'}`, background: intakeForm.urgency === u ? '#fdf8eb' : '#fff' }}>
                  <input type="radio" name="urgency" checked={intakeForm.urgency === u} onChange={() => setIntakeForm(p => ({ ...p, urgency: u }))} />
                  {u === 'standard' ? 'Standard (5-10 days)' : u === 'rush' ? 'Rush (+$50)' : 'Same Day — DC Only (+$100)'}
                </label>
              ))}
            </div>
          </div>
          <div>
            <label style={labelStyle}>Payment Preference</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {(['pay-now', 'pay-later', 'invoice'] as const).map(p => (
                <label key={p} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer', padding: '8px 12px', borderRadius: 8, border: `1px solid ${intakeForm.paymentPreference === p ? '#b8960c' : '#ece8e0'}`, background: intakeForm.paymentPreference === p ? '#fdf8eb' : '#fff' }}>
                  <input type="radio" name="payment" checked={intakeForm.paymentPreference === p} onChange={() => setIntakeForm(prev => ({ ...prev, paymentPreference: p }))} />
                  {p === 'pay-now' ? 'Pay Now' : p === 'pay-later' ? 'Pay Later' : 'Invoice'}
                </label>
              ))}
            </div>
          </div>
          <div>
            <label style={labelStyle}>How did you hear about us?</label>
            <select value={intakeForm.referralSource} onChange={e => setIntakeForm(p => ({ ...p, referralSource: e.target.value }))} style={inputStyle}>
              <option value="">Select...</option>
              <option value="google">Google Search</option>
              <option value="referral">Referral</option>
              <option value="social">Social Media</option>
              <option value="repeat">Repeat Customer</option>
              <option value="lawyer">Attorney/Lawyer</option>
              <option value="other">Other</option>
            </select>
            <div style={{ marginTop: 16 }}>
              <label style={labelStyle}>Notes / Special Instructions</label>
              <textarea value={intakeForm.notes} onChange={e => setIntakeForm(p => ({ ...p, notes: e.target.value }))} placeholder="Any special requests or notes..." rows={3}
                style={{ ...inputStyle, resize: 'vertical' }} />
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="empire-card" style={{ padding: 20, background: '#fdf8eb', border: '2px solid #b8960c' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>Client Intake Complete</div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>{intakeForm.documents.length} document{intakeForm.documents.length !== 1 ? 's' : ''} to process</div>
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <button onClick={saveClientProfile} disabled={!intakeForm.fullName || !intakeForm.email}
              style={{ padding: '12px 24px', background: intakeForm.fullName && intakeForm.email ? '#16a34a' : '#d1d5db', color: '#fff', borderRadius: 8, border: 'none', cursor: intakeForm.fullName && intakeForm.email ? 'pointer' : 'not-allowed', fontWeight: 700, fontSize: 13 }}>
              Save Client Profile
            </button>
            <button onClick={startOrderFromIntake} disabled={!intakeForm.fullName || intakeForm.documents.length === 0}
              style={{ padding: '12px 24px', background: intakeForm.fullName && intakeForm.documents.length > 0 ? '#b8960c' : '#d1d5db', color: '#fff', borderRadius: 8, border: 'none', cursor: intakeForm.fullName && intakeForm.documents.length > 0 ? 'pointer' : 'not-allowed', fontWeight: 700, fontSize: 13 }}>
              Start Order from Intake
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  const downloadFromLibrary = async (form: typeof FORMS_LIBRARY[0]) => {
    try {
      const emptyFields: Record<string, string> = {};
      form.fields.forEach(f => { emptyFields[f] = ''; });
      const res = await fetch(`${API}/apostapp/forms/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          form_name: form.name,
          agency: form.agency,
          purpose: form.purpose,
          fee: form.fee,
          fields: emptyFields,
          client_name: '',
          order_number: '',
          notes: 'Blank form — fill in fields before submitting',
        }),
      });
      if (res.ok) {
        const html = await res.text();
        const blob = new Blob([html], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const win = window.open(url, '_blank');
        if (win) win.focus();
      }
    } catch { alert('Failed to generate form. Make sure the backend is running.'); }
  };

  const renderFormsLibrary = () => {
    const filtered = formsSearch
      ? FORMS_LIBRARY.filter(f => f.name.toLowerCase().includes(formsSearch.toLowerCase()) || f.agency.toLowerCase().includes(formsSearch.toLowerCase()) || f.purpose.toLowerCase().includes(formsSearch.toLowerCase()))
      : FORMS_LIBRARY;

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#6b7280' }} />
            <input value={formsSearch} onChange={e => setFormsSearch(e.target.value)}
              placeholder="Search forms by name, agency, or purpose..."
              style={{ width: '100%', padding: '10px 12px 10px 34px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#faf9f7', outline: 'none' }} />
          </div>
          <div style={{ fontSize: 12, color: '#6b7280' }}>{filtered.length} form{filtered.length !== 1 ? 's' : ''}</div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
          {filtered.map((form, i) => (
            <div key={i} className="empire-card" style={{ padding: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>{form.name}</div>
                  <div style={{ fontSize: 11, color: '#b8960c', fontWeight: 600, marginTop: 2 }}>{form.agency}</div>
                </div>
                <span style={{ background: '#fdf8eb', color: '#b8960c', padding: '4px 12px', borderRadius: 999, fontSize: 12, fontWeight: 700 }}>{form.fee}</span>
              </div>
              <div style={{ fontSize: 13, color: '#374151', marginBottom: 12 }}>{form.purpose}</div>
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', marginBottom: 6 }}>Required Fields:</div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {form.fields.map(f => (
                    <span key={f} style={{ background: '#f3f4f6', padding: '2px 10px', borderRadius: 999, fontSize: 11, color: '#374151' }}>
                      {f.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={() => downloadFromLibrary(form)}
                  style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, padding: '8px 14px', background: '#faf9f7', color: '#374151', borderRadius: 8, border: '1px solid #ece8e0', cursor: 'pointer', fontWeight: 600, fontSize: 12 }}>
                  <ExternalLink size={14} /> Download
                </button>
                <button onClick={() => { setAiFillForm(form.name); setActiveSection('ai-fill'); }}
                  style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, padding: '8px 14px', background: '#b8960c', color: '#fff', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 12 }}>
                  <Zap size={14} /> Auto-Fill with AI
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderAIFill = () => {
    const selectedForm = FORMS_LIBRARY.find(f => f.name === aiFillForm);
    const selectedClient = savedClients.find(c => c.id === aiFillClient);
    const selectedOrder = orders.find(o => o.id === aiFillOrder);

    const autoFillFields = () => {
      if (!selectedForm) return;
      const fieldMap: Record<string, string> = {};

      const clientData: Record<string, string> = {
        applicant_name: selectedClient?.fullName || '', name: selectedClient?.fullName || '', applicant: selectedClient?.fullName || '',
        requester: selectedClient?.fullName || '', person_name: selectedClient?.fullName || '', signer_name: selectedClient?.fullName || '',
        responsible_party: selectedClient?.fullName || '', business_name: '',
        address: `${selectedClient?.street || ''}, ${selectedClient?.city || ''}, ${selectedClient?.state || ''} ${selectedClient?.zip || ''}`.replace(/^, /, ''),
        dob: selectedClient?.dateOfBirth || '', ssn: selectedClient?.ssnLast4 ? `***-**-${selectedClient.ssnLast4}` : '',
        document_type: selectedClient?.documents?.[0]?.docType || ((selectedOrder as any)?.documents?.[0]?.doc_type as any) || '',
        date_of_document: new Date().toISOString().split('T')[0],
        destination_country: selectedClient?.documents?.[0]?.destinationCountry || ((selectedOrder as any)?.documents?.[0]?.destination_country as any) || '',
        document_description: (selectedClient?.documents || []).map((d: any) => d.docType).join(', ') || ((selectedOrder as any)?.documents || []).map((d: any) => d.doc_type).join(', ') || '',
        document_info: (selectedClient?.documents || []).map((d: any) => d.docType).join(', ') || ((selectedOrder as any)?.documents || []).map((d: any) => d.doc_type).join(', ') || '',
        notary_info: '', notary_county: '', notary_details: '', notary_name: '', commission_expiry: '',
        state: selectedClient?.state || ((selectedOrder as any)?.documents?.[0]?.state_of_origin as any) || '',
        date: new Date().toISOString().split('T')[0],
        type: selectedClient?.documents?.[0]?.docType || ((selectedOrder as any)?.documents?.[0]?.doc_type as any) || '', relationship: '', purpose: '',
        fingerprints: 'Required — schedule at local FBI office or approved merchant',
        notaries: '',
      };

      selectedForm.fields.forEach(f => {
        fieldMap[f] = clientData[f] || '';
      });
      setAiFillFields(fieldMap);
      setAiFillGenerated(false);
    };

    const downloadForm = async () => {
      if (!selectedForm) return;
      const clientName = selectedClient?.fullName || selectedOrder?.customer?.name || '';
      const orderNumber = selectedOrder?.orderNumber || (selectedOrder as any)?.order_number || '';
      try {
        const res = await fetch(`${API}/apostapp/forms/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            form_name: selectedForm.name,
            agency: selectedForm.agency,
            purpose: selectedForm.purpose,
            fee: selectedForm.fee,
            fields: aiFillFields,
            client_name: clientName,
            order_number: orderNumber,
            notes: '',
          }),
        });
        if (res.ok) {
          const html = await res.text();
          const blob = new Blob([html], { type: 'text/html' });
          const url = URL.createObjectURL(blob);
          const win = window.open(url, '_blank');
          if (win) win.focus();
        }
      } catch { alert('Failed to generate form. Make sure the backend is running.'); }
    };

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Selection */}
        <div className="empire-card" style={{ padding: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Zap size={16} style={{ color: '#b8960c' }} /> AI Form Assist
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 12, alignItems: 'end' }}>
            <div>
              <label style={labelStyle}>Select Form</label>
              <select value={aiFillForm} onChange={e => { setAiFillForm(e.target.value); setAiFillFields({}); setAiFillGenerated(false); }} style={inputStyle}>
                <option value="">Choose a form...</option>
                {FORMS_LIBRARY.map(f => <option key={f.name} value={f.name}>{f.name} — {f.agency}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Select Client</label>
              <select value={aiFillClient} onChange={e => { setAiFillClient(e.target.value); setAiFillFields({}); setAiFillGenerated(false); }} style={inputStyle}>
                <option value="">Choose a saved client...</option>
                {savedClients.map(c => <option key={c.id} value={c.id}>{c.fullName} ({c.email})</option>)}
              </select>
            </div>
            <button onClick={autoFillFields} disabled={!aiFillForm}
              style={{ padding: '8px 20px', background: aiFillForm ? '#b8960c' : '#d1d5db', color: '#fff', borderRadius: 8, border: 'none', cursor: aiFillForm ? 'pointer' : 'not-allowed', fontWeight: 600, fontSize: 13, height: 38 }}>
              Auto-Fill
            </button>
          </div>

          {/* Order selector row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 12 }}>
            <div>
              <label style={labelStyle}>Select Order (optional — for real order data)</label>
              <select value={aiFillOrder} onChange={e => { setAiFillOrder(e.target.value); setAiFillFields({}); setAiFillGenerated(false); }} style={inputStyle}>
                <option value="">Choose an order...</option>
                {orders.map(o => <option key={o.id} value={o.id}>{o.orderNumber || o.id} — {o.customer?.name || (o as any).customer_name || 'No name'}</option>)}
              </select>
            </div>
            {selectedOrder && (
              <div style={{ padding: '8px 12px', background: '#f0fdf4', borderRadius: 8, border: '1px solid #bbf7d0', fontSize: 12, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                <div style={{ fontWeight: 600 }}>{selectedOrder.customer?.name || (selectedOrder as any).customer_name || '—'}</div>
                <div style={{ color: '#6b7280' }}>{selectedOrder.documents?.length || 0} doc(s) · {selectedOrder.status} · {selectedOrder.shippingMethod || (selectedOrder as any).shipping_method || 'standard'}</div>
                <div style={{ color: '#6b7280' }}>{selectedOrder.documents?.[0]?.destinationCountry || (selectedOrder.documents?.[0] as any)?.destination_country || ''}</div>
              </div>
            )}
          </div>

          {(savedClients.length === 0 && orders.length === 0) && (
            <div style={{ marginTop: 12, padding: 12, background: '#fef3c7', borderRadius: 8, fontSize: 12, color: '#92400e', display: 'flex', alignItems: 'center', gap: 8 }}>
              <AlertTriangle size={14} /> No clients or orders yet. Use Client Intake or create an order first.
            </div>
          )}
        </div>

        {/* Preview Panel */}
        {selectedForm && Object.keys(aiFillFields).length > 0 && (
          <div className="empire-card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{selectedForm.name} — Preview</div>
                <div style={{ fontSize: 11, color: '#6b7280' }}>{selectedForm.agency} | Fee: {selectedForm.fee}</div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={() => setAiFillGenerated(true)}
                  style={{ padding: '8px 16px', background: '#faf9f7', color: '#374151', borderRadius: 8, border: '1px solid #ece8e0', cursor: 'pointer', fontWeight: 600, fontSize: 12 }}>
                  Show Text
                </button>
                <button onClick={downloadForm}
                  style={{ padding: '8px 16px', background: '#16a34a', color: '#fff', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 12 }}>
                  Print / Save PDF
                </button>
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {selectedForm.fields.map(field => {
                const value = aiFillFields[field] || '';
                const isAutoFilled = !!value;
                return (
                  <div key={field} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 12px', borderRadius: 8, background: isAutoFilled ? '#f0fdf4' : '#fef3c7', border: `1px solid ${isAutoFilled ? '#bbf7d0' : '#fbbf24'}` }}>
                    <div style={{ width: 180, fontSize: 12, fontWeight: 600, color: '#374151' }}>
                      {field.replace(/_/g, ' ')}
                      {!isAutoFilled && <span style={{ color: '#d97706', marginLeft: 4, fontSize: 10, fontWeight: 700 }}>MISSING</span>}
                      {isAutoFilled && <span style={{ color: '#16a34a', marginLeft: 4, fontSize: 10, fontWeight: 700 }}>FILLED</span>}
                    </div>
                    <input value={value} onChange={e => setAiFillFields(prev => ({ ...prev, [field]: e.target.value }))}
                      placeholder={`Enter ${field.replace(/_/g, ' ')}...`}
                      style={{ flex: 1, padding: '6px 10px', borderRadius: 6, border: '1px solid #ece8e0', fontSize: 13, background: '#fff', outline: 'none' }} />
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Generated Text Version */}
        {aiFillGenerated && selectedForm && (
          <div className="empire-card" style={{ padding: 20, background: '#faf9f7' }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Form Data Summary</div>
            <pre style={{ fontFamily: 'monospace', fontSize: 12, lineHeight: 1.8, padding: 16, background: '#fff', borderRadius: 8, border: '1px solid #ece8e0', whiteSpace: 'pre-wrap' }}>
{`FORM: ${selectedForm.name}
AGENCY: ${selectedForm.agency}
PURPOSE: ${selectedForm.purpose}
FEE: ${selectedForm.fee}
DATE GENERATED: ${new Date().toISOString().split('T')[0]}
${'='.repeat(50)}

${selectedForm.fields.map(f => `${f.replace(/_/g, ' ').toUpperCase()}: ${aiFillFields[f] || '[NOT PROVIDED — fill in manually]'}`).join('\n')}`}
            </pre>
          </div>
        )}
      </div>
    );
  };

  const renderNotary = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Explanation */}
      <div className="empire-card" style={{ padding: 20, background: '#fdf8eb', border: '2px solid #b8960c' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
          <div style={{ width: 44, height: 44, borderRadius: 10, background: '#b8960c', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Shield size={22} style={{ color: '#fff' }} />
          </div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700 }}>Remote Online Notarization (RON)</div>
            <div style={{ fontSize: 13, color: '#6b7280' }}>Legally valid document notarization via live video call</div>
          </div>
        </div>
        <p style={{ fontSize: 13, color: '#374151', lineHeight: 1.6, margin: 0 }}>
          Remote Online Notarization allows documents to be notarized via live video call — legally valid in DC, MD, and VA.
          Signers verify their identity through knowledge-based authentication (KBA) and credential analysis, then sign electronically
          while a commissioned notary applies their digital seal and certificate. The entire session is recorded for compliance.
        </p>
      </div>

      {/* State Compliance */}
      <div className="empire-card" style={{ overflow: 'hidden' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid #ece8e0' }}>
          <div style={{ fontSize: 14, fontWeight: 600 }}>State Compliance</div>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#faf9f7', borderBottom: '1px solid #ece8e0' }}>
              <th style={{ textAlign: 'left', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>State</th>
              <th style={{ textAlign: 'center', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Authorized</th>
              <th style={{ textAlign: 'center', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Since</th>
              <th style={{ textAlign: 'left', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Notes</th>
            </tr>
          </thead>
          <tbody>
            {RON_STATES.map(s => (
              <tr key={s.state} style={{ borderBottom: '1px solid #ece8e0' }}>
                <td style={{ padding: '12px 14px', fontWeight: 600 }}>{s.state}</td>
                <td style={{ padding: '12px 14px', textAlign: 'center' }}>
                  <span style={{ background: '#dcfce7', color: '#16a34a', padding: '2px 10px', borderRadius: 999, fontSize: 11, fontWeight: 600 }}>{s.authorized}</span>
                </td>
                <td style={{ padding: '12px 14px', textAlign: 'center', fontWeight: 600 }}>{s.since}</td>
                <td style={{ padding: '12px 14px', color: '#6b7280', fontSize: 12 }}>{s.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Platform Integrations */}
      <div className="empire-card" style={{ padding: 20 }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14 }}>RON Platform Integrations</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14 }}>
          {RON_PLATFORMS.map(p => (
            <div key={p.name} style={{ padding: 16, borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div style={{ fontSize: 14, fontWeight: 700 }}>{p.name}</div>
                <span style={{ background: '#fdf8eb', color: '#b8960c', padding: '3px 10px', borderRadius: 999, fontSize: 11, fontWeight: 700 }}>{p.price}</span>
              </div>
              <div style={{ fontSize: 12, color: '#6b7280', lineHeight: 1.5 }}>{p.description}</div>
            </div>
          ))}
        </div>
      </div>

      {/* In-House Notary */}
      <div className="empire-card" style={{ padding: 20, border: '2px solid #b8960c' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ width: 52, height: 52, borderRadius: '50%', background: '#b8960c18', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <User size={24} style={{ color: '#b8960c' }} />
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700 }}>Empire Notary — Juan Diego Giraldo</div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>Commissioned in DC / MD / VA</div>
            <div style={{ fontSize: 12, color: '#16a34a', fontWeight: 600, marginTop: 2 }}>Available Mon-Fri 9:00 AM - 5:00 PM</div>
          </div>
          <div style={{ marginLeft: 'auto' }}>
            <span style={{ background: '#dcfce7', color: '#16a34a', padding: '4px 12px', borderRadius: 999, fontSize: 12, fontWeight: 600 }}>In-House</span>
          </div>
        </div>
      </div>

      {/* Session Scheduling */}
      <div className="empire-card" style={{ padding: 20 }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Calendar size={16} style={{ color: '#b8960c' }} /> Schedule RON Session
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr', gap: 12, alignItems: 'end' }}>
          <div>
            <label style={labelStyle}>Client Name</label>
            <input value={ronSessionForm.clientName} onChange={e => setRonSessionForm(p => ({ ...p, clientName: e.target.value }))} placeholder="Client name" style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Document Type</label>
            <select value={ronSessionForm.docType} onChange={e => setRonSessionForm(p => ({ ...p, docType: e.target.value }))} style={inputStyle}>
              <option value="">Select...</option>
              {DOC_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Preferred Date</label>
            <input type="date" value={ronSessionForm.preferredDate} onChange={e => setRonSessionForm(p => ({ ...p, preferredDate: e.target.value }))} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Preferred Time</label>
            <input type="time" value={ronSessionForm.preferredTime} onChange={e => setRonSessionForm(p => ({ ...p, preferredTime: e.target.value }))} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>State</label>
            <select value={ronSessionForm.state} onChange={e => setRonSessionForm(p => ({ ...p, state: e.target.value }))} style={inputStyle}>
              <option value="DC">DC</option>
              <option value="MD">MD</option>
              <option value="VA">VA</option>
            </select>
          </div>
        </div>
        <div style={{ marginTop: 14 }}>
          <button onClick={() => { alert(`RON session scheduled for ${ronSessionForm.clientName} on ${ronSessionForm.preferredDate} at ${ronSessionForm.preferredTime}`); }}
            disabled={!ronSessionForm.clientName || !ronSessionForm.preferredDate}
            style={{ padding: '10px 24px', background: ronSessionForm.clientName && ronSessionForm.preferredDate ? '#b8960c' : '#d1d5db', color: '#fff', borderRadius: 8, border: 'none', cursor: ronSessionForm.clientName && ronSessionForm.preferredDate ? 'pointer' : 'not-allowed', fontWeight: 600, fontSize: 13 }}>
            Schedule RON Session
          </button>
        </div>
      </div>
    </div>
  );

  const renderESign = () => {
    const eSignStatusColors: Record<string, { bg: string; color: string }> = {
      pending: { bg: '#f3f4f6', color: '#6b7280' },
      viewed: { bg: '#dbeafe', color: '#2563eb' },
      signed: { bg: '#dcfce7', color: '#16a34a' },
      declined: { bg: '#fee2e2', color: '#dc2626' },
    };

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Platform Comparison */}
        <div className="empire-card" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid #ece8e0' }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>E-Signature Platform Comparison</div>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#faf9f7', borderBottom: '1px solid #ece8e0' }}>
                <th style={{ textAlign: 'left', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Platform</th>
                <th style={{ textAlign: 'center', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Price</th>
                <th style={{ textAlign: 'left', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Features</th>
                <th style={{ textAlign: 'center', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Integration</th>
              </tr>
            </thead>
            <tbody>
              {ESIGN_PLATFORMS.map((p, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #ece8e0' }}>
                  <td style={{ padding: '12px 14px', fontWeight: 600 }}>{p.name}</td>
                  <td style={{ padding: '12px 14px', textAlign: 'center', fontWeight: 600, color: '#b8960c' }}>{p.price}</td>
                  <td style={{ padding: '12px 14px', color: '#6b7280' }}>{p.features}</td>
                  <td style={{ padding: '12px 14px', textAlign: 'center' }}>
                    <span style={{ background: '#dcfce7', color: '#16a34a', padding: '2px 10px', borderRadius: 999, fontSize: 11, fontWeight: 600 }}>{p.integration}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Send for Signature */}
        <div className="empire-card" style={{ padding: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircle size={16} style={{ color: '#b8960c' }} /> Send for Signature
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={labelStyle}>Document Name</label>
              <input value={eSignForm.documentName} onChange={e => setESignForm(p => ({ ...p, documentName: e.target.value }))} placeholder="e.g. Power of Attorney - Martinez" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Recipient Email</label>
              <input type="email" value={eSignForm.recipientEmail} onChange={e => setESignForm(p => ({ ...p, recipientEmail: e.target.value }))} placeholder="recipient@example.com" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Message</label>
              <input value={eSignForm.message} onChange={e => setESignForm(p => ({ ...p, message: e.target.value }))} placeholder="Please review and sign this document" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Deadline</label>
              <input type="date" value={eSignForm.deadline} onChange={e => setESignForm(p => ({ ...p, deadline: e.target.value }))} style={inputStyle} />
            </div>
          </div>
          <div style={{ marginTop: 14 }}>
            <button onClick={() => {
              if (!eSignForm.documentName || !eSignForm.recipientEmail) return;
              const newDoc: ESignDocument = {
                id: `es-${Date.now()}`, name: eSignForm.documentName, recipient: eSignForm.recipientEmail,
                sentDate: new Date().toISOString().split('T')[0], deadline: eSignForm.deadline || 'N/A',
                status: 'pending', platform: 'DocuSign',
              };
              setESignDocs(prev => [newDoc, ...prev]);
              setESignForm({ documentName: '', recipientEmail: '', message: '', deadline: '' });
            }}
              disabled={!eSignForm.documentName || !eSignForm.recipientEmail}
              style={{ padding: '10px 24px', background: eSignForm.documentName && eSignForm.recipientEmail ? '#b8960c' : '#d1d5db', color: '#fff', borderRadius: 8, border: 'none', cursor: eSignForm.documentName && eSignForm.recipientEmail ? 'pointer' : 'not-allowed', fontWeight: 600, fontSize: 13 }}>
              Send for Signature
            </button>
          </div>
        </div>

        {/* Signature Status Tracker */}
        <div className="empire-card" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid #ece8e0' }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>Signature Status Tracker</div>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#faf9f7', borderBottom: '1px solid #ece8e0' }}>
                <th style={{ textAlign: 'left', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Document</th>
                <th style={{ textAlign: 'left', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Recipient</th>
                <th style={{ textAlign: 'center', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Platform</th>
                <th style={{ textAlign: 'center', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Sent</th>
                <th style={{ textAlign: 'center', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Deadline</th>
                <th style={{ textAlign: 'center', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {eSignDocs.map(doc => {
                const sc = eSignStatusColors[doc.status] || eSignStatusColors.pending;
                return (
                  <tr key={doc.id} style={{ borderBottom: '1px solid #ece8e0' }}>
                    <td style={{ padding: '12px 14px', fontWeight: 600 }}>{doc.name}</td>
                    <td style={{ padding: '12px 14px', color: '#6b7280' }}>{doc.recipient}</td>
                    <td style={{ padding: '12px 14px', textAlign: 'center' }}>{doc.platform}</td>
                    <td style={{ padding: '12px 14px', textAlign: 'center', color: '#6b7280' }}>{doc.sentDate}</td>
                    <td style={{ padding: '12px 14px', textAlign: 'center', color: '#6b7280' }}>{doc.deadline}</td>
                    <td style={{ padding: '12px 14px', textAlign: 'center' }}>
                      <span style={{ background: sc.bg, color: sc.color, padding: '2px 10px', borderRadius: 999, fontSize: 11, fontWeight: 600, textTransform: 'capitalize' }}>
                        {doc.status}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {eSignDocs.length === 0 && (
            <div style={{ padding: 40, textAlign: 'center', color: '#6b7280', fontSize: 13 }}>No documents sent for signature yet</div>
          )}
        </div>
      </div>
    );
  };

  const renderCouriers = () => {
    const filteredCouriers = courierContacts.filter(c => {
      if (courierStateFilter !== 'all' && !c.states.includes(courierStateFilter)) return false;
      if (courierServiceFilter !== 'all' && !c.services.some(s => s.toLowerCase().includes(courierServiceFilter.toLowerCase()))) return false;
      if (courierSearch && !c.name.toLowerCase().includes(courierSearch.toLowerCase()) && !c.company.toLowerCase().includes(courierSearch.toLowerCase())) return false;
      return true;
    });

    const deliveryStatusColors: Record<string, { bg: string; color: string; label: string }> = {
      'pickup-scheduled': { bg: '#f3f4f6', color: '#6b7280', label: 'Pickup Scheduled' },
      'in-transit': { bg: '#dbeafe', color: '#2563eb', label: 'In Transit' },
      'delivered': { bg: '#dcfce7', color: '#16a34a', label: 'Delivered' },
    };

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Search & Filters */}
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#6b7280' }} />
            <input value={courierSearch} onChange={e => setCourierSearch(e.target.value)}
              placeholder="Search couriers by name or company..."
              style={{ width: '100%', padding: '10px 12px 10px 34px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#faf9f7', outline: 'none' }} />
          </div>
          <select value={courierStateFilter} onChange={e => setCourierStateFilter(e.target.value)}
            style={{ padding: '10px 14px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#faf9f7', outline: 'none' }}>
            <option value="all">All States</option>
            <option value="DC">DC</option>
            <option value="MD">MD</option>
            <option value="VA">VA</option>
          </select>
          <select value={courierServiceFilter} onChange={e => setCourierServiceFilter(e.target.value)}
            style={{ padding: '10px 14px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, background: '#faf9f7', outline: 'none' }}>
            <option value="all">All Services</option>
            <option value="same-day">Same-day</option>
            <option value="rush">Rush</option>
            <option value="standard">Standard</option>
            <option value="government">Government Drop-off</option>
            <option value="embassy">Embassy Runs</option>
          </select>
        </div>

        {/* Courier Directory */}
        <div className="empire-card" style={{ padding: 20 }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Truck size={16} style={{ color: '#b8960c' }} /> Courier Directory
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14 }}>
            {filteredCouriers.map(c => (
              <div key={c.id} style={{ padding: 16, borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700 }}>{c.name}</div>
                    <div style={{ fontSize: 12, color: '#b8960c', fontWeight: 600 }}>{c.company}</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Star size={14} style={{ color: '#b8960c', fill: '#b8960c' }} />
                    <span style={{ fontSize: 13, fontWeight: 700 }}>{c.rating}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#6b7280' }}>
                    <Phone size={12} /> {c.phone}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#6b7280' }}>
                    <Mail size={12} /> {c.email}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 4, marginBottom: 8, flexWrap: 'wrap' }}>
                  {c.states.map(s => (
                    <span key={s} style={{ background: '#b8960c18', color: '#b8960c', padding: '2px 8px', borderRadius: 999, fontSize: 10, fontWeight: 700 }}>{s}</span>
                  ))}
                </div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {c.services.map(s => (
                    <span key={s} style={{ background: '#f3f4f6', padding: '2px 8px', borderRadius: 999, fontSize: 10, color: '#374151' }}>{s}</span>
                  ))}
                </div>
              </div>
            ))}
            {filteredCouriers.length === 0 && (
              <div style={{ gridColumn: '1 / -1', padding: 30, textAlign: 'center', color: '#6b7280', fontSize: 13 }}>No couriers match your search criteria</div>
            )}
          </div>
        </div>

        {/* Active Deliveries */}
        <div className="empire-card" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid #ece8e0' }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>Active Deliveries</div>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#faf9f7', borderBottom: '1px solid #ece8e0' }}>
                <th style={{ textAlign: 'left', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Courier</th>
                <th style={{ textAlign: 'left', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Order #</th>
                <th style={{ textAlign: 'left', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Pickup</th>
                <th style={{ textAlign: 'left', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Destination</th>
                <th style={{ textAlign: 'center', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>Status</th>
                <th style={{ textAlign: 'right', padding: '10px 14px', fontWeight: 600, color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>ETA</th>
              </tr>
            </thead>
            <tbody>
              {courierDeliveries.map(d => {
                const ds = deliveryStatusColors[d.status] || deliveryStatusColors['pickup-scheduled'];
                return (
                  <tr key={d.id} style={{ borderBottom: '1px solid #ece8e0' }}>
                    <td style={{ padding: '12px 14px', fontWeight: 600 }}>{d.courier}</td>
                    <td style={{ padding: '12px 14px', color: '#b8960c', fontWeight: 600 }}>{d.orderNumber}</td>
                    <td style={{ padding: '12px 14px', color: '#6b7280' }}>{d.pickup}</td>
                    <td style={{ padding: '12px 14px', color: '#6b7280' }}>{d.destination}</td>
                    <td style={{ padding: '12px 14px', textAlign: 'center' }}>
                      <span style={{ background: ds.bg, color: ds.color, padding: '2px 10px', borderRadius: 999, fontSize: 11, fontWeight: 600 }}>{ds.label}</span>
                    </td>
                    <td style={{ padding: '12px 14px', textAlign: 'right', color: '#6b7280', fontSize: 12 }}>{d.eta}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {courierDeliveries.length === 0 && (
            <div style={{ padding: 40, textAlign: 'center', color: '#6b7280', fontSize: 13 }}>No courier deliveries scheduled</div>
          )}
        </div>
      </div>
    );
  };

  // ============ MAIN RENDER ============

  const renderContent = () => {
    switch (activeSection) {
      case 'overview': return renderOverview();
      case 'orders': return renderOrders();
      case 'new-order': return renderNewOrder();
      case 'customers': return renderCustomers();
      case 'pricing': return renderPricing();
      case 'llc-integration': return renderLLCIntegration();
      case 'tracking': return renderTracking();
      case 'intake': return renderIntake();
      case 'forms': return renderFormsLibrary();
      case 'ai-fill': return renderAIFill();
      case 'notary': return renderNotary();
      case 'e-sign': return renderESign();
      case 'couriers': return renderCouriers();
      case 'payments': return <div style={{ padding: 24 }}><PaymentModule product="apost" amount={0} /></div>;
      case 'docs': return <div style={{ padding: 24 }}><ProductDocs product="apost" /></div>;
      case 'transcript':
        if (onNavigate) { onNavigate('transcript', 'dashboard'); }
        return <div style={{ padding: 24, textAlign: 'center', color: '#6b7280' }}>Opening TranscriptForge...</div>;
      default: return renderOverview();
    }
  };

  return (
    <div style={{ display: 'flex', height: '100%', background: '#faf9f7' }}>
      {/* Left Sidebar */}
      <div style={{ width: 200, borderRight: '1px solid #ece8e0', background: '#fff', display: 'flex', flexDirection: 'column', padding: '16px 0', flexShrink: 0 }}>
        <div style={{ padding: '0 16px 16px', borderBottom: '1px solid #ece8e0', marginBottom: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 28, height: 28, borderRadius: 6, background: '#b8960c18', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <StampIcon size={16} style={{ color: '#b8960c' }} />
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>ApostApp</div>
              <div style={{ fontSize: 10, color: '#6b7280' }}>Document Apostille Services</div>
            </div>
          </div>
        </div>
        {NAV_SECTIONS.map(s => {
          const isActive = activeSection === s.id;
          const iconEl = typeof s.icon === 'function'
            ? React.createElement(s.icon as any, { size: 15, style: { color: isActive ? '#b8960c' : '#6b7280' } })
            : s.icon;
          return (
            <button key={s.id} onClick={() => setActiveSection(s.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 10, width: '100%', padding: '9px 16px',
                background: isActive ? '#fdf8eb' : 'transparent', border: 'none', cursor: 'pointer',
                borderRight: isActive ? '3px solid #b8960c' : '3px solid transparent',
                transition: 'all 0.15s',
              }}>
              <span style={{ color: isActive ? '#b8960c' : '#6b7280', display: 'flex', alignItems: 'center' }}>{iconEl}</span>
              <span style={{ fontSize: 13, fontWeight: isActive ? 600 : 400, color: isActive ? '#b8960c' : '#374151' }}>{s.label}</span>
            </button>
          );
        })}
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: '24px 28px' }}>
        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <Loader2 size={24} className="animate-spin" style={{ color: '#b8960c' }} />
          </div>
        ) : (
          renderContent()
        )}
      </div>
    </div>
  );
}
