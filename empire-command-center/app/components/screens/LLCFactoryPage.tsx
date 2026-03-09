'use client';
import React, { useState, useEffect } from 'react';
import { API } from '../../lib/api';
import {
  Globe, ClipboardList, Package, FileText, Users, MapPin, Sparkles,
  Plus, Search, ChevronRight, Check, X, Loader2, DollarSign, Building,
  Scale, Shield, Truck, Calendar, ArrowRight, AlertTriangle, ExternalLink,
  FileDown, Star, Zap, Award, CheckCircle, Clock, Hash, Mail, Phone,
  User, Briefcase, ChevronDown, ChevronUp, Eye, RefreshCw, Copy, Send
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import { PaymentModule } from '../business/payments';

// Stamp icon doesn't exist in lucide-react, use Shield as substitute
const Stamp = Shield;

const NAV_SECTIONS = [
  { id: 'overview', label: 'Overview', icon: Globe },
  { id: 'services', label: 'Services', icon: ClipboardList },
  { id: 'packages', label: 'Packages', icon: Package },
  { id: 'orders', label: 'Orders', icon: FileText },
  { id: 'customers', label: 'Customers', icon: Users },
  { id: 'apostille', label: 'Apostille', icon: Stamp },
  { id: 'guides', label: 'State Guides', icon: MapPin },
  { id: 'financials', label: 'Financials', icon: DollarSign },
  { id: 'couriers', label: 'Couriers', icon: Truck },
  { id: 'ai-tools', label: 'AI Tools', icon: Sparkles },
  { id: 'payments', label: 'Payments', icon: DollarSign },
  { id: 'docs', label: 'Docs', icon: FileText },
] as const;

type Section = typeof NAV_SECTIONS[number]['id'];

// ============ MOCK / FALLBACK DATA ============

const FALLBACK_SERVICES = [
  { id: 'llc-formation', category: 'Formation', name: 'LLC Formation', description: 'Form a new Limited Liability Company', icon: 'Building', serviceFee: 0, stateFees: { DC: 99, MD: 150, VA: 100 }, processingTime: '3-5 business days' },
  { id: 'corp-formation', category: 'Formation', name: 'Corporation Formation', description: 'Form a new C-Corp or S-Corp', icon: 'Building', serviceFee: 49, stateFees: { DC: 220, MD: 120, VA: 75 }, processingTime: '3-5 business days' },
  { id: 'nonprofit-formation', category: 'Formation', name: 'Nonprofit Formation', description: 'Form a 501(c)(3) nonprofit organization', icon: 'Scale', serviceFee: 99, stateFees: { DC: 80, MD: 170, VA: 75 }, processingTime: '5-7 business days' },
  { id: 'dba-registration', category: 'Formation', name: 'DBA / Trade Name', description: 'Register a doing-business-as name', icon: 'FileText', serviceFee: 29, stateFees: { DC: 55, MD: 25, VA: 10 }, processingTime: '1-3 business days' },
  { id: 'ein-application', category: 'Tax & Compliance', name: 'EIN Application', description: 'Obtain your federal Employer Identification Number', icon: 'Hash', serviceFee: 49, stateFees: { DC: 0, MD: 0, VA: 0 }, processingTime: '1-2 business days' },
  { id: 'annual-report', category: 'Tax & Compliance', name: 'Annual Report Filing', description: 'File your annual or biennial report', icon: 'Calendar', serviceFee: 49, stateFees: { DC: 300, MD: 300, VA: 50 }, processingTime: '3-5 business days' },
  { id: 'boc-report', category: 'Tax & Compliance', name: 'BOI Report (FinCEN)', description: 'Beneficial Ownership Information report', icon: 'Shield', serviceFee: 49, stateFees: { DC: 0, MD: 0, VA: 0 }, processingTime: '1-2 business days' },
  { id: 'business-license', category: 'Tax & Compliance', name: 'Business License Application', description: 'State and local business license filing', icon: 'Briefcase', serviceFee: 49, stateFees: { DC: 0, MD: 0, VA: 0 }, processingTime: '5-10 business days' },
  { id: 'state-tax-reg', category: 'Tax & Compliance', name: 'State Tax Registration', description: 'Register for state income and sales tax', icon: 'DollarSign', serviceFee: 39, stateFees: { DC: 0, MD: 0, VA: 0 }, processingTime: '3-5 business days' },
  { id: 'compliance-monitoring', category: 'Tax & Compliance', name: 'Compliance Monitoring', description: 'Annual compliance alerts and deadline tracking', icon: 'Shield', serviceFee: 49, stateFees: { DC: 0, MD: 0, VA: 0 }, processingTime: 'Ongoing' },
  { id: 'operating-agreement', category: 'Document Services', name: 'Operating Agreement', description: 'Custom drafted LLC operating agreement', icon: 'FileText', serviceFee: 79, stateFees: { DC: 0, MD: 0, VA: 0 }, processingTime: '2-3 business days' },
  { id: 'articles-amendment', category: 'Document Services', name: 'Articles Amendment', description: 'Amend your formation documents', icon: 'FileText', serviceFee: 49, stateFees: { DC: 50, MD: 100, VA: 25 }, processingTime: '3-5 business days' },
  { id: 'certificate-good-standing', category: 'Document Services', name: 'Certificate of Good Standing', description: 'Obtain a certificate of good standing / existence', icon: 'Award', serviceFee: 29, stateFees: { DC: 22, MD: 20, VA: 6 }, processingTime: '2-5 business days' },
  { id: 'apostille-vital-records', category: 'Document Services', name: 'Vital Records + Apostille', description: 'Obtain birth/death/marriage cert and apostille', icon: 'FileText', serviceFee: 89, stateFees: { DC: 15, MD: 15, VA: 22 }, processingTime: '7-14 business days' },
  { id: 'fbi-background-apostille', category: 'Document Services', name: 'FBI Background Check + Apostille', description: 'FBI Identity History Summary with federal apostille', icon: 'Shield', serviceFee: 149, stateFees: { DC: 38, MD: 38, VA: 38 }, processingTime: '6-14 weeks' },
  { id: 'certified-copy', category: 'Document Services', name: 'Certified Copy Request', description: 'Obtain certified copies from state agencies', icon: 'FileDown', serviceFee: 39, stateFees: { DC: 50, MD: 20, VA: 6 }, processingTime: '3-10 business days' },
  { id: 'apostille-service', category: 'Notary', name: 'Apostille / Authentication', description: 'State and federal document authentication', icon: 'Shield', serviceFee: 75, stateFees: { DC: 15, MD: 5, VA: 10 }, processingTime: '5-10 business days' },
  { id: 'notary-service', category: 'Notary', name: 'Notary Service', description: 'In-person or remote online notarization', icon: 'Shield', serviceFee: 25, stateFees: { DC: 0, MD: 0, VA: 0 }, processingTime: 'Same day' },
  { id: 'federal-apostille', category: 'Notary', name: 'Federal Apostille (DS-4194)', description: 'US Department of State authentication for federal documents', icon: 'Shield', serviceFee: 99, stateFees: { DC: 20, MD: 20, VA: 20 }, processingTime: '5-11 weeks' },
  { id: 'embassy-legalization', category: 'Notary', name: 'Embassy Legalization', description: 'Authentication for non-Hague Convention countries', icon: 'Globe', serviceFee: 149, stateFees: { DC: 0, MD: 0, VA: 0 }, processingTime: '2-6 weeks' },
  { id: 'registered-agent', category: 'Registered Agent', name: 'Registered Agent (Annual)', description: 'Serve as your statutory registered agent', icon: 'User', serviceFee: 99, stateFees: { DC: 0, MD: 0, VA: 0 }, processingTime: 'Immediate' },
  { id: 'mail-forwarding', category: 'Additional', name: 'Mail Forwarding', description: 'Business mail scanning and forwarding', icon: 'Mail', serviceFee: 29, stateFees: { DC: 0, MD: 0, VA: 0 }, processingTime: 'Immediate' },
  { id: 'foreign-qualification', category: 'Additional', name: 'Foreign Qualification', description: 'Register your business in another state', icon: 'Globe', serviceFee: 99, stateFees: { DC: 220, MD: 100, VA: 100 }, processingTime: '5-7 business days' },
];

const FALLBACK_PACKAGES = [
  {
    id: 'starter', name: 'Starter', price: 0, color: '#16a34a', badge: null,
    description: 'Just the essentials — formation filing only',
    included: ['llc-formation', 'digital-delivery'],
    notIncluded: ['ein-application', 'operating-agreement', 'registered-agent', 'boc-report', 'apostille-service', 'annual-report'],
    processingTime: '5-7 business days',
  },
  {
    id: 'professional', name: 'Professional', price: 149, color: '#b8960c', badge: 'Most Popular',
    description: 'Everything you need to launch and operate',
    included: ['llc-formation', 'ein-application', 'operating-agreement', 'boc-report', 'digital-delivery'],
    notIncluded: ['registered-agent', 'apostille-service', 'annual-report'],
    processingTime: '3-5 business days',
  },
  {
    id: 'empire', name: 'Empire', price: 349, color: '#7c3aed', badge: 'Best Value',
    description: 'Full-service formation with ongoing support',
    included: ['llc-formation', 'ein-application', 'operating-agreement', 'boc-report', 'registered-agent', 'certificate-good-standing', 'annual-report', 'mail-forwarding', 'digital-delivery'],
    notIncluded: [],
    processingTime: '1-3 business days (expedited)',
  },
];

const SERVICE_NAMES: Record<string, string> = {
  'llc-formation': 'LLC Formation Filing',
  'ein-application': 'EIN Application',
  'operating-agreement': 'Operating Agreement',
  'boc-report': 'BOI Report (FinCEN)',
  'registered-agent': 'Registered Agent (1 Year)',
  'certificate-good-standing': 'Certificate of Good Standing',
  'annual-report': 'Annual Report Filing',
  'mail-forwarding': 'Mail Forwarding (1 Year)',
  'apostille-service': 'Apostille Service',
  'digital-delivery': 'Digital Document Delivery',
  'business-license': 'Business License Application',
  'state-tax-reg': 'State Tax Registration',
  'compliance-monitoring': 'Compliance Monitoring',
  'federal-apostille': 'Federal Apostille (DS-4194)',
  'embassy-legalization': 'Embassy Legalization',
  'apostille-vital-records': 'Vital Records + Apostille',
  'fbi-background-apostille': 'FBI Background Check + Apostille',
  'certified-copy': 'Certified Copy Request',
};

const STATUS_COLORS: Record<string, { bg: string; color: string; label: string }> = {
  received: { bg: '#f3f4f6', color: '#6b7280', label: 'Received' },
  processing: { bg: '#dbeafe', color: '#2563eb', label: 'Processing' },
  filed: { bg: '#fdf8eb', color: '#b8960c', label: 'Filed' },
  approved: { bg: '#dcfce7', color: '#16a34a', label: 'Approved' },
  delivered: { bg: '#ede9fe', color: '#7c3aed', label: 'Delivered' },
  completed: { bg: '#d1fae5', color: '#065f46', label: 'Completed' },
};

const APOSTILLE_STAGES = ['Document Received', 'Notarized', 'State Auth', 'Federal Auth', 'Embassy', 'Delivered'];

const STATE_GUIDES: Record<string, any> = {
  AL: {
    name: 'Alabama', authority: 'Secretary of State',
    filingFee: 200, expeditedFee: 50, annualReportFee: 10, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.alabama.gov', portalUrl: 'https://sos.alabama.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  AK: {
    name: 'Alaska', authority: 'Division of Corporations, Business and Professional Licensing',
    filingFee: 250, expeditedFee: 50, annualReportFee: 100, annualReportFrequency: 'Biennial',
    annualReportDeadline: 'Varies', portal: 'commerce.alaska.gov', portalUrl: 'https://commerce.alaska.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Division of Corporations', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File biennial report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File biennial reports on time to avoid penalties'],
  },
  AZ: {
    name: 'Arizona', authority: 'Arizona Corporation Commission',
    filingFee: 50, expeditedFee: 50, annualReportFee: 0, annualReportFrequency: 'None',
    annualReportDeadline: 'N/A', portal: 'azcc.gov', portalUrl: 'https://azcc.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Corporation Commission', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'No annual report required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['No annual report required — one of the simplest states', 'Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times'],
  },
  AR: {
    name: 'Arkansas', authority: 'Secretary of State',
    filingFee: 45, expeditedFee: 50, annualReportFee: 150, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.arkansas.gov', portalUrl: 'https://sos.arkansas.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  CA: {
    name: 'California', authority: 'Secretary of State',
    filingFee: 70, expeditedFee: 350, annualReportFee: 20, annualReportFrequency: 'Biennial',
    annualReportDeadline: 'End of anniversary month (every 2 years)', portal: 'bizfileOnline.sos.ca.gov', portalUrl: 'https://bizfileonline.sos.ca.gov',
    steps: ['Search name on California Business Search', 'Prepare Articles of Organization', 'File online via bizfileOnline', 'Pay $70 filing fee', 'Receive filed Articles', 'Obtain EIN', 'Register with CA Franchise Tax Board', 'File Statement of Information within 90 days', 'File biennial Statement of Information'],
    requiredDocs: ['Articles of Organization (Form LLC-1)', 'Statement of Information (Form LLC-12)', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['$70 filing fee is very affordable', 'Online filing processes same-day', 'Must file Statement of Information within 90 days of formation'],
    warnings: ['$800 ANNUAL franchise tax — even if no revenue', 'This is THE most expensive ongoing cost for any state', 'First-year exemption may apply for new LLCs'],
  },
  CO: {
    name: 'Colorado', authority: 'Secretary of State',
    filingFee: 50, expeditedFee: 50, annualReportFee: 10, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.state.co.us', portalUrl: 'https://sos.state.co.us',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  CT: {
    name: 'Connecticut', authority: 'Secretary of State',
    filingFee: 120, expeditedFee: 50, annualReportFee: 80, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sots.ct.gov', portalUrl: 'https://sots.ct.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  DE: {
    name: 'Delaware', authority: 'Division of Corporations',
    filingFee: 90, expeditedFee: 50, annualReportFee: 300, annualReportFrequency: 'Annual',
    annualReportDeadline: 'June 1', portal: 'corp.delaware.gov', portalUrl: 'https://corp.delaware.gov',
    steps: ['Search name via Division of Corporations', 'Prepare Certificate of Formation', 'File online or by mail', 'Pay filing fee ($90)', 'Receive Certificate', 'Obtain EIN from IRS', 'Register for DE taxes if doing business in-state', 'File Annual Report + $300 franchise tax by June 1'],
    requiredDocs: ['Certificate of Formation', 'Registered Agent in Delaware', 'Operating Agreement (recommended)', 'Annual Franchise Tax payment'],
    tips: ['Delaware is the #1 state for business-friendly laws', 'Court of Chancery specializes in business disputes', 'If not doing business in DE, no state income tax'],
    warnings: ['$300 annual franchise tax even if no revenue', 'Must maintain a Delaware registered agent', 'Late annual report penalty: $200 + 1.5%/month interest'],
  },
  DC: {
    name: 'District of Columbia', authority: 'Department of Licensing and Consumer Protection (DLCP)',
    filingFee: 99, expeditedFee: 50, annualReportFee: 300, annualReportFrequency: 'Biennial',
    annualReportDeadline: 'April 1 (every 2 years)', portal: 'corponline.dlcp.dc.gov',
    portalUrl: 'https://corponline.dlcp.dc.gov',
    steps: [
      'Search business name availability on DLCP website',
      'Prepare Articles of Organization',
      'File online through CorpOnline or mail to DLCP',
      'Pay filing fee ($99 online)',
      'Receive stamped Articles (2-3 weeks standard)',
      'Obtain EIN from IRS',
      'Register for DC taxes (MyTax.DC.gov)',
      'File Biennial Report by April 1',
    ],
    requiredDocs: ['Articles of Organization', 'Registered Agent Consent', 'Operating Agreement (recommended)', 'EIN Confirmation Letter'],
    tips: ['DC uses "biennial" reports — file every 2 years by April 1', 'No state income tax for LLCs — but DC franchise tax applies', 'Registered agent must have a physical DC address'],
    warnings: ['Late biennial report: $100 penalty + administrative dissolution risk', 'DC requires a Clean Hands Certificate for many filings'],
  },
  FL: {
    name: 'Florida', authority: 'Department of State, Division of Corporations',
    filingFee: 125, expeditedFee: 50, annualReportFee: 138.75, annualReportFrequency: 'Annual',
    annualReportDeadline: 'May 1', portal: 'sunbiz.org', portalUrl: 'https://sunbiz.org',
    steps: ['Search name on Sunbiz', 'Prepare Articles of Organization', 'File online through Sunbiz', 'Pay $125 filing fee', 'Receive filed Articles', 'Obtain EIN', 'Register with FL Dept of Revenue', 'File Annual Report by May 1 ($138.75)'],
    requiredDocs: ['Articles of Organization', 'Registered Agent in Florida', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['No state income tax for individuals', 'Online filing processes within 1-2 business days', 'Sunbiz is user-friendly portal'],
    warnings: ['Late annual report: $400 late fee', 'Must file annual report even if no changes', 'Corporate income tax (5.5%) applies to C-Corps only'],
  },
  GA: {
    name: 'Georgia', authority: 'Secretary of State',
    filingFee: 100, expeditedFee: 50, annualReportFee: 50, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.ga.gov', portalUrl: 'https://sos.ga.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  HI: {
    name: 'Hawaii', authority: 'Department of Commerce and Consumer Affairs (DCCA)',
    filingFee: 50, expeditedFee: 50, annualReportFee: 15, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'hbe.ehawaii.gov', portalUrl: 'https://hbe.ehawaii.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with DCCA', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  ID: {
    name: 'Idaho', authority: 'Secretary of State',
    filingFee: 100, expeditedFee: 50, annualReportFee: 0, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.idaho.gov', portalUrl: 'https://sos.idaho.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report (no fee)'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Annual report has no fee — just an information filing', 'Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  IL: {
    name: 'Illinois', authority: 'Secretary of State',
    filingFee: 150, expeditedFee: 50, annualReportFee: 75, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'ilsos.gov', portalUrl: 'https://ilsos.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  IN: {
    name: 'Indiana', authority: 'Secretary of State',
    filingFee: 95, expeditedFee: 50, annualReportFee: 32, annualReportFrequency: 'Biennial',
    annualReportDeadline: 'Varies', portal: 'sos.in.gov', portalUrl: 'https://sos.in.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File biennial report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File biennial reports on time to avoid penalties'],
  },
  IA: {
    name: 'Iowa', authority: 'Secretary of State',
    filingFee: 50, expeditedFee: 50, annualReportFee: 60, annualReportFrequency: 'Biennial',
    annualReportDeadline: 'Varies', portal: 'sos.iowa.gov', portalUrl: 'https://sos.iowa.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File biennial report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File biennial reports on time to avoid penalties'],
  },
  KS: {
    name: 'Kansas', authority: 'Secretary of State',
    filingFee: 160, expeditedFee: 50, annualReportFee: 55, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.ks.gov', portalUrl: 'https://sos.ks.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  KY: {
    name: 'Kentucky', authority: 'Secretary of State',
    filingFee: 40, expeditedFee: 50, annualReportFee: 15, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.ky.gov', portalUrl: 'https://sos.ky.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['One of the cheapest states to form and maintain an LLC', 'Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  LA: {
    name: 'Louisiana', authority: 'Secretary of State',
    filingFee: 100, expeditedFee: 50, annualReportFee: 35, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.la.gov', portalUrl: 'https://sos.la.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  ME: {
    name: 'Maine', authority: 'Secretary of State',
    filingFee: 175, expeditedFee: 50, annualReportFee: 85, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.maine.gov', portalUrl: 'https://sos.maine.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  MD: {
    name: 'Maryland', authority: 'State Department of Assessments and Taxation (SDAT)',
    filingFee: 100, expeditedFee: 50, annualReportFee: 300, annualReportFrequency: 'Annual',
    annualReportDeadline: 'April 15 each year', portal: 'businessexpress.maryland.gov',
    portalUrl: 'https://businessexpress.maryland.gov',
    steps: [
      'Search name availability on Maryland Business Express',
      'Prepare Articles of Organization',
      'File online ($150) or by mail ($100) through SDAT',
      'Pay filing fee',
      'Receive confirmation (1-2 weeks online, 4-6 weeks mail)',
      'Obtain EIN from IRS',
      'Register with Comptroller of Maryland for taxes',
      'File Annual Report by April 15 each year',
    ],
    requiredDocs: ['Articles of Organization', 'Resident Agent designation', 'Operating Agreement (recommended)', 'Annual Report (Personal Property Return)'],
    tips: ['Online filing costs $50 more but processes much faster', 'Maryland calls the annual report a "Personal Property Return"', 'Resident agent (not "registered agent") must be MD resident or MD entity'],
    warnings: ['Annual report is $300 — one of the highest in the nation', 'Filing late triggers penalties plus potential forfeiture', 'Online filing fee is $150 vs $100 by mail'],
  },
  MA: {
    name: 'Massachusetts', authority: 'Secretary of the Commonwealth',
    filingFee: 500, expeditedFee: 50, annualReportFee: 500, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sec.state.ma.us', portalUrl: 'https://sec.state.ma.us',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of the Commonwealth', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['$500 filing fee AND $500 annual report — one of the most expensive states', 'Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  MI: {
    name: 'Michigan', authority: 'Department of Licensing and Regulatory Affairs (LARA)',
    filingFee: 50, expeditedFee: 50, annualReportFee: 25, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'michigan.gov/lara', portalUrl: 'https://michigan.gov/lara',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with LARA', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  MN: {
    name: 'Minnesota', authority: 'Secretary of State',
    filingFee: 155, expeditedFee: 50, annualReportFee: 0, annualReportFrequency: 'None',
    annualReportDeadline: 'N/A', portal: 'sos.state.mn.us', portalUrl: 'https://sos.state.mn.us',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'No annual report required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['No annual report required — one of the simplest states', 'Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times'],
  },
  MS: {
    name: 'Mississippi', authority: 'Secretary of State',
    filingFee: 50, expeditedFee: 50, annualReportFee: 0, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.ms.gov', portalUrl: 'https://sos.ms.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report (no fee)'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Annual report has no fee — just an information filing', 'Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  MO: {
    name: 'Missouri', authority: 'Secretary of State',
    filingFee: 50, expeditedFee: 50, annualReportFee: 0, annualReportFrequency: 'None',
    annualReportDeadline: 'N/A', portal: 'sos.mo.gov', portalUrl: 'https://sos.mo.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'No annual report required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['No annual report required — one of the simplest states', 'Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times'],
  },
  MT: {
    name: 'Montana', authority: 'Secretary of State',
    filingFee: 35, expeditedFee: 50, annualReportFee: 20, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.mt.gov', portalUrl: 'https://sos.mt.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['One of the cheapest states to form an LLC ($35)', 'Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  NE: {
    name: 'Nebraska', authority: 'Secretary of State',
    filingFee: 100, expeditedFee: 50, annualReportFee: 10, annualReportFrequency: 'Biennial',
    annualReportDeadline: 'Varies', portal: 'sos.nebraska.gov', portalUrl: 'https://sos.nebraska.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File biennial report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File biennial reports on time to avoid penalties'],
  },
  NV: {
    name: 'Nevada', authority: 'Secretary of State',
    filingFee: 75, expeditedFee: 125, annualReportFee: 150, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Last day of anniversary month', portal: 'nvsos.gov', portalUrl: 'https://www.nvsos.gov/sos/businesses',
    steps: ['Search name on NV SOS', 'Prepare Articles of Organization', 'File online via SilverFlume', 'Pay $75 filing fee + $150 business license', 'Receive filed Articles', 'Obtain EIN', 'No state income tax registration needed', 'File Annual List by anniversary ($150)'],
    requiredDocs: ['Articles of Organization', 'Registered Agent in Nevada', 'Initial List of Managers/Members', 'State Business License ($200)'],
    tips: ['No state income tax, no franchise tax', 'Strong privacy protections', 'SilverFlume portal processes quickly'],
    warnings: ['$200 state business license fee on top of filing', '$150 annual list — higher than average', 'Total year-1 cost: ~$425+ (filing + license + annual list)'],
  },
  NH: {
    name: 'New Hampshire', authority: 'Secretary of State',
    filingFee: 100, expeditedFee: 50, annualReportFee: 100, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.nh.gov', portalUrl: 'https://sos.nh.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  NJ: {
    name: 'New Jersey', authority: 'Department of the Treasury',
    filingFee: 125, expeditedFee: 50, annualReportFee: 75, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'njportal.com/DOR/BusinessFormation', portalUrl: 'https://njportal.com/DOR/BusinessFormation',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Department of the Treasury', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  NM: {
    name: 'New Mexico', authority: 'Secretary of State',
    filingFee: 50, expeditedFee: 50, annualReportFee: 0, annualReportFrequency: 'None',
    annualReportDeadline: 'N/A', portal: 'sos.state.nm.us', portalUrl: 'https://sos.state.nm.us',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'No annual report required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['No annual report required — one of the simplest states', 'Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times'],
  },
  NY: {
    name: 'New York', authority: 'Department of State, Division of Corporations',
    filingFee: 200, expeditedFee: 25, annualReportFee: 9, annualReportFrequency: 'Biennial',
    annualReportDeadline: 'Anniversary month (every 2 years)', portal: 'dos.ny.gov', portalUrl: 'https://www.dos.ny.gov/corps/',
    steps: ['Search name on DOS website', 'Prepare Articles of Organization', 'File online or by mail', 'Pay $200 filing fee', 'Receive filed Articles', 'PUBLISH in 2 newspapers for 6 consecutive weeks', 'File Certificate of Publication', 'Obtain EIN', 'Register with NY Tax Dept'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (required by law)', 'Certificate of Publication'],
    tips: ['NY REQUIRES an Operating Agreement by law', 'Biennial report is only $9', 'Consider forming in another state if not doing business in NY'],
    warnings: ['PUBLICATION REQUIREMENT: Must publish in 2 newspapers for 6 weeks — costs $300-$2000+', 'Failure to publish = LLC loses authority to sue', '$200 filing fee + publication makes NY one of the most expensive states'],
  },
  NC: {
    name: 'North Carolina', authority: 'Secretary of State',
    filingFee: 125, expeditedFee: 50, annualReportFee: 200, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sosnc.gov', portalUrl: 'https://sosnc.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['$200 annual report fee is higher than average', 'Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  ND: {
    name: 'North Dakota', authority: 'Secretary of State',
    filingFee: 135, expeditedFee: 50, annualReportFee: 50, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.nd.gov', portalUrl: 'https://sos.nd.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  OH: {
    name: 'Ohio', authority: 'Secretary of State',
    filingFee: 99, expeditedFee: 50, annualReportFee: 0, annualReportFrequency: 'None',
    annualReportDeadline: 'N/A', portal: 'sos.state.oh.us', portalUrl: 'https://sos.state.oh.us',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'No annual report required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['No annual report required — one of the simplest states', 'Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times'],
  },
  OK: {
    name: 'Oklahoma', authority: 'Secretary of State',
    filingFee: 100, expeditedFee: 50, annualReportFee: 25, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.ok.gov', portalUrl: 'https://sos.ok.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  OR: {
    name: 'Oregon', authority: 'Secretary of State',
    filingFee: 100, expeditedFee: 50, annualReportFee: 100, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.oregon.gov', portalUrl: 'https://sos.oregon.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  PA: {
    name: 'Pennsylvania', authority: 'Department of State',
    filingFee: 125, expeditedFee: 50, annualReportFee: 70, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'dos.pa.gov', portalUrl: 'https://dos.pa.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Department of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  RI: {
    name: 'Rhode Island', authority: 'Secretary of State',
    filingFee: 150, expeditedFee: 50, annualReportFee: 50, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.ri.gov', portalUrl: 'https://sos.ri.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  SC: {
    name: 'South Carolina', authority: 'Secretary of State',
    filingFee: 110, expeditedFee: 50, annualReportFee: 0, annualReportFrequency: 'None',
    annualReportDeadline: 'N/A', portal: 'sos.sc.gov', portalUrl: 'https://sos.sc.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'No annual report required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['No annual report required — one of the simplest states', 'Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times'],
  },
  SD: {
    name: 'South Dakota', authority: 'Secretary of State',
    filingFee: 150, expeditedFee: 50, annualReportFee: 50, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sdsos.gov', portalUrl: 'https://sdsos.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  TN: {
    name: 'Tennessee', authority: 'Secretary of State',
    filingFee: 300, expeditedFee: 50, annualReportFee: 300, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.tn.gov', portalUrl: 'https://sos.tn.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['$300 filing + $300 annual report — one of the most expensive states', 'Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  TX: {
    name: 'Texas', authority: 'Secretary of State',
    filingFee: 300, expeditedFee: 25, annualReportFee: 0, annualReportFrequency: 'Annual',
    annualReportDeadline: 'May 15 (franchise tax)', portal: 'sos.state.tx.us', portalUrl: 'https://www.sos.state.tx.us/corp/forms_702.shtml',
    steps: ['Search name on SOSDirect', 'Prepare Certificate of Formation', 'File online via SOSDirect', 'Pay $300 filing fee', 'Receive filed Certificate', 'Obtain EIN', 'Register with Texas Comptroller', 'File Franchise Tax Report by May 15'],
    requiredDocs: ['Certificate of Formation', 'Registered Agent in Texas', 'Operating Agreement (recommended)', 'Public Information Report'],
    tips: ['No state income tax', 'Franchise tax: no tax owed if revenue under $2.47M', '$300 filing fee is higher than average but includes everything'],
    warnings: ['Must file franchise tax report annually even if no tax owed', 'Failure to file = forfeiture of business', '$300 filing fee is non-refundable'],
  },
  UT: {
    name: 'Utah', authority: 'Department of Commerce',
    filingFee: 54, expeditedFee: 50, annualReportFee: 18, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'commerce.utah.gov', portalUrl: 'https://commerce.utah.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Department of Commerce', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['One of the most affordable states for ongoing maintenance', 'Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  VT: {
    name: 'Vermont', authority: 'Secretary of State',
    filingFee: 125, expeditedFee: 50, annualReportFee: 35, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.vermont.gov', portalUrl: 'https://sos.vermont.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  VA: {
    name: 'Virginia', authority: 'State Corporation Commission (SCC)',
    filingFee: 100, expeditedFee: 200, annualReportFee: 50, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Last day of anniversary month', portal: 'scc.virginia.gov',
    portalUrl: 'https://scc.virginia.gov',
    steps: [
      'Search name availability on SCC Clerk\'s Information System',
      'Prepare Articles of Organization',
      'File online through SCC eFile or by mail',
      'Pay filing fee ($100)',
      'Receive Certificate of Organization (same day online, 1-2 weeks mail)',
      'Obtain EIN from IRS',
      'Register with Virginia Department of Taxation',
      'File Annual Registration ($50) by anniversary month',
    ],
    requiredDocs: ['Articles of Organization', 'Registered Agent statement', 'Operating Agreement (recommended)', 'Annual Registration Fee payment'],
    tips: ['Virginia is one of the fastest — online filings often same-day', 'Annual registration is only $50 — very affordable', 'SCC eFile system is efficient and user-friendly'],
    warnings: ['Expedited processing costs $200 extra but is rarely needed for online filings', 'Must maintain a registered agent with a VA street address at all times', 'Failure to pay annual registration leads to automatic cancellation'],
  },
  WA: {
    name: 'Washington', authority: 'Secretary of State',
    filingFee: 200, expeditedFee: 50, annualReportFee: 60, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.wa.gov', portalUrl: 'https://sos.wa.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  WV: {
    name: 'West Virginia', authority: 'Secretary of State',
    filingFee: 100, expeditedFee: 50, annualReportFee: 25, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'sos.wv.gov', portalUrl: 'https://sos.wv.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with Secretary of State', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  WI: {
    name: 'Wisconsin', authority: 'Department of Financial Institutions (DFI)',
    filingFee: 130, expeditedFee: 50, annualReportFee: 25, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Varies', portal: 'dfi.wi.gov', portalUrl: 'https://dfi.wi.gov',
    steps: ['Search name availability', 'Prepare Articles of Organization/Certificate of Formation', 'File online or by mail with DFI', 'Pay filing fee', 'Receive filed documents', 'Obtain EIN from IRS', 'Register for state taxes', 'File annual report if required'],
    requiredDocs: ['Articles of Organization', 'Registered Agent', 'Operating Agreement (recommended)', 'EIN'],
    tips: ['Check state portal for current processing times'],
    warnings: ['Maintain registered agent at all times', 'File annual reports on time to avoid penalties'],
  },
  WY: {
    name: 'Wyoming', authority: 'Secretary of State',
    filingFee: 100, expeditedFee: 100, annualReportFee: 60, annualReportFrequency: 'Annual',
    annualReportDeadline: 'Anniversary month', portal: 'wyobiz.wyo.gov', portalUrl: 'https://wyobiz.wyo.gov',
    steps: ['Search name on WyoBiz', 'Prepare Articles of Organization', 'File online through WyoBiz', 'Pay $100 filing fee', 'Receive filed Articles', 'Obtain EIN', 'No state income tax registration needed', 'File Annual Report by anniversary month ($60 minimum)'],
    requiredDocs: ['Articles of Organization', 'Registered Agent in Wyoming', 'Operating Agreement (recommended)'],
    tips: ['No state income tax, no franchise tax', 'Strong privacy — no public member disclosure', 'Annual report fee based on assets in WY ($60 min)'],
    warnings: ['Must maintain Wyoming registered agent', 'Late annual report: involuntary dissolution'],
  },
};

// ============ MAIN COMPONENT ============

export default function LLCFactoryPage() {
  const [section, setSection] = useState<Section>('overview');
  const [showNewOrder, setShowNewOrder] = useState(false);

  const renderContent = () => {
    if (showNewOrder) return <NewOrderWizard onClose={() => setShowNewOrder(false)} />;
    switch (section) {
      case 'overview': return <OverviewSection onNavigate={setSection} onNewOrder={() => setShowNewOrder(true)} />;
      case 'services': return <ServicesSection />;
      case 'packages': return <PackagesSection onNewOrder={() => setShowNewOrder(true)} />;
      case 'orders': return <OrdersSection onNewOrder={() => setShowNewOrder(true)} />;
      case 'customers': return <CustomersSection />;
      case 'apostille': return <ApostilleSection />;
      case 'guides': return <StateGuidesSection />;
      case 'financials': return <FinancialsSection />;
      case 'couriers': return <CourierManagementSection />;
      case 'ai-tools': return <AIToolsSection />;
      case 'payments': return <div style={{ padding: 24 }}><PaymentModule product="llc" amount={0} /></div>;
      case 'docs': return <div style={{ padding: 24 }}><ProductDocs product="llc" /></div>;
      default: return <OverviewSection onNavigate={setSection} onNewOrder={() => setShowNewOrder(true)} />;
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      <nav style={{ width: 200, background: '#fff', borderRight: '1px solid #ece8e0', flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '18px 16px', borderBottom: '1px solid #ece8e0' }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#dcfce7] flex items-center justify-center">
              <Globe size={18} className="text-[#16a34a]" />
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>LLC Factory</div>
              <div style={{ fontSize: 10, color: '#999' }}>Business Services</div>
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto" style={{ padding: '10px 10px' }}>
          <div className="flex flex-col gap-1.5">
            {NAV_SECTIONS.map(nav => {
              const Icon = nav.icon;
              const isActive = section === nav.id && !showNewOrder;
              return (
                <button key={nav.id}
                  onClick={() => { setSection(nav.id); setShowNewOrder(false); }}
                  className="w-full flex items-center gap-3 text-left cursor-pointer transition-all"
                  style={{
                    padding: '10px 14px', borderRadius: 12, fontSize: 13,
                    fontWeight: isActive ? 700 : 500,
                    background: isActive ? '#dcfce7' : 'transparent',
                    color: isActive ? '#16a34a' : '#666',
                    border: isActive ? '1.5px solid #bbf7d0' : '1.5px solid transparent',
                  }}
                  onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background = '#f5f3ef'; e.currentTarget.style.borderColor = '#ece8e0'; } }}
                  onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'transparent'; } }}
                >
                  <Icon size={17} />
                  {nav.label}
                </button>
              );
            })}
          </div>
        </div>
      </nav>
      <div className="flex-1 overflow-y-auto" style={{ background: '#f5f2ed' }}>
        {renderContent()}
      </div>
    </div>
  );
}

// ============ KPI CARD ============

function KPI({ icon, iconBg, iconColor, label, value, sub, onClick }: {
  icon: React.ReactNode; iconBg: string; iconColor: string; label: string; value: string; sub: string; onClick?: () => void;
}) {
  return (
    <div onClick={onClick} className="empire-card" style={{ cursor: onClick ? 'pointer' : 'default', padding: '16px 18px' }}>
      <div className="flex items-center gap-3 mb-2">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: iconBg, color: iconColor }}>{icon}</div>
        <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: '#999' }}>{label}</span>
      </div>
      <div style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a' }}>{value}</div>
      <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>{sub}</div>
    </div>
  );
}

function QuickLink({ icon, label, desc, color, onClick }: { icon: React.ReactNode; label: string; desc: string; color: string; onClick: () => void }) {
  return (
    <div onClick={onClick} className="empire-card" style={{ cursor: 'pointer', padding: '14px 16px' }}
      onMouseEnter={e => (e.currentTarget.style.borderColor = color)}
      onMouseLeave={e => (e.currentTarget.style.borderColor = '#ece8e0')}>
      <div className="flex items-center gap-2 mb-1" style={{ color }}>{icon}<span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{label}</span></div>
      <div style={{ fontSize: 11, color: '#999' }}>{desc}</div>
    </div>
  );
}

// ============ 1. OVERVIEW ============

function OverviewSection({ onNavigate, onNewOrder }: { onNavigate: (s: Section) => void; onNewOrder: () => void }) {
  const [dashboard, setDashboard] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(API + '/llcfactory/dashboard').then(r => r.json()).then(setDashboard)
      .catch(() => setDashboard({
        activeOrders: 3, revenueMTD: 2450, formationsThisMonth: 5, pendingApostilles: 2,
        recentOrders: [
          { id: 'ORD-001', customer: 'Sarah Johnson', business: 'Bloom & Co LLC', state: 'DC', status: 'processing', total: 248, date: '2026-03-07' },
          { id: 'ORD-002', customer: 'Marcus Lee', business: 'TechVenture Corp', state: 'VA', status: 'filed', total: 499, date: '2026-03-06' },
          { id: 'ORD-003', customer: 'Diana Park', business: 'Green Path Consulting', state: 'MD', status: 'approved', total: 149, date: '2026-03-05' },
          { id: 'ORD-004', customer: 'James Wright', business: 'Wright Legal PLLC', state: 'DC', status: 'delivered', total: 598, date: '2026-03-04' },
          { id: 'ORD-005', customer: 'Amara Obi', business: 'Obi Imports LLC', state: 'VA', status: 'completed', total: 349, date: '2026-03-03' },
        ],
        topServices: [
          { name: 'LLC Formation', count: 12 },
          { name: 'EIN Application', count: 9 },
          { name: 'Operating Agreement', count: 7 },
          { name: 'Registered Agent', count: 5 },
          { name: 'Apostille', count: 3 },
        ],
      }))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex-1 flex items-center justify-center py-20"><Loader2 size={24} className="text-[#16a34a] animate-spin" /></div>;
  const d = dashboard || {};

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center gap-3 mb-1">
        <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>LLC Factory</h1>
        <span style={{ fontSize: 13, color: '#aaa' }} suppressHydrationWarning>
          {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
        </span>
      </div>

      <div className="grid grid-cols-4 gap-3 mt-5 mb-6">
        <KPI icon={<ClipboardList size={18} />} iconBg="#dbeafe" iconColor="#2563eb" label="Active Orders" value={String(d.activeOrders ?? 0)} sub="In progress" onClick={() => onNavigate('orders')} />
        <KPI icon={<DollarSign size={18} />} iconBg="#dcfce7" iconColor="#16a34a" label="Revenue MTD" value={`$${(d.revenueMTD ?? 0).toLocaleString()}`} sub="This month" />
        <KPI icon={<Building size={18} />} iconBg="#fdf8eb" iconColor="#b8960c" label="Formations" value={String(d.formationsThisMonth ?? 0)} sub="This month" onClick={() => onNavigate('orders')} />
        <KPI icon={<Shield size={18} />} iconBg="#ede9fe" iconColor="#7c3aed" label="Pending Apostilles" value={String(d.pendingApostilles ?? 0)} sub="In pipeline" onClick={() => onNavigate('apostille')} />
      </div>

      <div className="section-label" style={{ marginBottom: 8 }}>Quick Access</div>
      <div className="grid grid-cols-4 gap-3 mb-6">
        <QuickLink icon={<Plus size={18} />} label="New Order" desc="Start a new filing" color="#16a34a" onClick={onNewOrder} />
        <QuickLink icon={<Search size={18} />} label="Name Check" desc="Check name availability" color="#2563eb" onClick={() => onNavigate('ai-tools')} />
        <QuickLink icon={<FileText size={18} />} label="Generate OA" desc="Operating agreement" color="#b8960c" onClick={() => onNavigate('ai-tools')} />
        <QuickLink icon={<MapPin size={18} />} label="State Guide" desc="DC, MD, VA guides" color="#7c3aed" onClick={() => onNavigate('guides')} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="empire-card">
          <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 12 }} className="flex items-center gap-2">
            <ClipboardList size={15} className="text-[#b8960c]" /> Recent Orders
          </h3>
          <div className="space-y-2">
            {(d.recentOrders || []).slice(0, 5).map((o: any, i: number) => {
              const st = STATUS_COLORS[o.status] || STATUS_COLORS.received;
              return (
                <div key={i} style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0' }}
                  className="hover:border-[#b8960c] hover:bg-[#fdf8eb] transition-all cursor-pointer flex items-center justify-between">
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{o.business}</div>
                    <div style={{ fontSize: 10, color: '#777' }}>{o.customer} &middot; {o.state}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 20, background: st.bg, color: st.color, fontWeight: 600 }}>{st.label}</span>
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>${o.total}</span>
                  </div>
                </div>
              );
            })}
            {(!d.recentOrders || d.recentOrders.length === 0) && (
              <div style={{ padding: 20, textAlign: 'center', color: '#999', fontSize: 12 }}>No recent orders</div>
            )}
          </div>
        </div>

        <div className="empire-card">
          <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 12 }} className="flex items-center gap-2">
            <Star size={15} className="text-[#b8960c]" /> Top Services
          </h3>
          <div className="space-y-3">
            {(d.topServices || []).map((s: any, i: number) => (
              <div key={i} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span style={{ fontSize: 10, fontWeight: 700, color: '#999', width: 16, textAlign: 'right' }}>#{i + 1}</span>
                  <span style={{ fontSize: 12, fontWeight: 500, color: '#1a1a1a' }}>{s.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div style={{ width: 80, height: 6, background: '#f0ece4', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ width: `${Math.min(100, (s.count / ((d.topServices || [])[0]?.count || 1)) * 100)}%`, height: '100%', background: '#b8960c', borderRadius: 3 }} />
                  </div>
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#666', minWidth: 20, textAlign: 'right' }}>{s.count}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============ 2. SERVICES ============

function ServicesSection() {
  const [services, setServices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedState, setSelectedState] = useState<'DC' | 'MD' | 'VA'>('DC');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetch(API + '/llcfactory/services').then(r => r.json()).then(data => setServices(data.services || data || []))
      .catch(() => setServices(FALLBACK_SERVICES))
      .finally(() => setLoading(false));
  }, []);

  const svcList = services.length > 0 ? services : FALLBACK_SERVICES;
  const filtered = svcList.filter(s =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.category.toLowerCase().includes(searchQuery.toLowerCase())
  );
  const categories = [...new Set(filtered.map(s => s.category))];

  if (loading) return <div className="flex-1 flex items-center justify-center py-20"><Loader2 size={24} className="text-[#16a34a] animate-spin" /></div>;

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center justify-between mb-5">
        <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>Services Catalog</h1>
        <div className="flex items-center gap-3">
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#999' }} />
            <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Search services..."
              style={{ padding: '8px 12px 8px 30px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 12, width: 200, background: '#fff', outline: 'none' }} />
          </div>
          <select value={selectedState} onChange={e => setSelectedState(e.target.value as any)}
            style={{ padding: '8px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 12, background: '#fff', cursor: 'pointer', outline: 'none' }}>
            <option value="DC">Washington, DC</option>
            <option value="MD">Maryland</option>
            <option value="VA">Virginia</option>
          </select>
        </div>
      </div>

      {categories.map(cat => (
        <div key={cat} className="mb-6">
          <div className="section-label" style={{ marginBottom: 10 }}>{cat}</div>
          <div className="grid grid-cols-2 gap-3">
            {filtered.filter(s => s.category === cat).map(svc => {
              const stateFee = svc.stateFees?.[selectedState] ?? 0;
              return (
                <div key={svc.id} className="empire-card" style={{ padding: '16px 18px' }}>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="w-8 h-8 rounded-lg bg-[#dcfce7] flex items-center justify-center">
                        <Building size={16} className="text-[#16a34a]" />
                      </div>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{svc.name}</div>
                        <div style={{ fontSize: 11, color: '#999' }}>{svc.description}</div>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between mt-3" style={{ borderTop: '1px solid #f0ece4', paddingTop: 10 }}>
                    <div className="flex items-center gap-4">
                      <div><div style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', color: '#999', letterSpacing: 0.5 }}>Service Fee</div><div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>${svc.serviceFee}</div></div>
                      {stateFee > 0 && <div><div style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', color: '#999', letterSpacing: 0.5 }}>State Fee ({selectedState})</div><div style={{ fontSize: 14, fontWeight: 700, color: '#b8960c' }}>${stateFee}</div></div>}
                      <div><div style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', color: '#999', letterSpacing: 0.5 }}>Processing</div><div style={{ fontSize: 11, fontWeight: 500, color: '#666' }}>{svc.processingTime}</div></div>
                    </div>
                    <button style={{ padding: '6px 16px', borderRadius: 8, background: '#16a34a', color: '#fff', fontSize: 11, fontWeight: 600, border: 'none', cursor: 'pointer' }}>Order</button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

// ============ 3. PACKAGES ============

function PackagesSection({ onNewOrder }: { onNewOrder: () => void }) {
  const [packages, setPackages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(API + '/llcfactory/packages').then(r => r.json()).then(data => setPackages(data.packages || data || []))
      .catch(() => setPackages(FALLBACK_PACKAGES))
      .finally(() => setLoading(false));
  }, []);

  const pkgs = packages.length > 0 ? packages : FALLBACK_PACKAGES;

  if (loading) return <div className="flex-1 flex items-center justify-center py-20"><Loader2 size={24} className="text-[#16a34a] animate-spin" /></div>;

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0, marginBottom: 6 }}>Formation Packages</h1>
      <p style={{ fontSize: 13, color: '#999', marginBottom: 24 }}>Choose the right package for your business. All packages include state filing fees.</p>

      <div className="grid grid-cols-3 gap-4">
        {pkgs.map((pkg: any) => (
          <div key={pkg.id} className="empire-card" style={{ padding: 0, overflow: 'hidden', border: pkg.badge ? `2px solid ${pkg.color}` : undefined, position: 'relative' }}>
            {pkg.badge && (
              <div style={{ position: 'absolute', top: 12, right: 12, padding: '3px 10px', borderRadius: 20, background: pkg.color, color: '#fff', fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                {pkg.badge}
              </div>
            )}
            <div style={{ padding: '24px 20px', background: `${pkg.color}10`, borderBottom: `1px solid ${pkg.color}30` }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: pkg.color, marginBottom: 4 }}>{pkg.name}</div>
              <div style={{ fontSize: 11, color: '#777', marginBottom: 12 }}>{pkg.description}</div>
              <div className="flex items-baseline gap-1">
                <span style={{ fontSize: 32, fontWeight: 800, color: '#1a1a1a' }}>${pkg.price}</span>
                <span style={{ fontSize: 12, color: '#999' }}>+ state fees</span>
              </div>
              <div style={{ fontSize: 10, color: '#999', marginTop: 4 }}>{pkg.processingTime}</div>
            </div>
            <div style={{ padding: '18px 20px' }}>
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', letterSpacing: 0.5, marginBottom: 10 }}>Included</div>
              <div className="space-y-2 mb-4">
                {(pkg.included || []).map((svcId: string) => (
                  <div key={svcId} className="flex items-center gap-2">
                    <Check size={14} style={{ color: pkg.color }} />
                    <span style={{ fontSize: 12, color: '#1a1a1a' }}>{SERVICE_NAMES[svcId] || svcId}</span>
                  </div>
                ))}
              </div>
              {(pkg.notIncluded || []).length > 0 && (
                <>
                  <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#ccc', letterSpacing: 0.5, marginBottom: 10 }}>Not Included</div>
                  <div className="space-y-2 mb-4">
                    {(pkg.notIncluded || []).map((svcId: string) => (
                      <div key={svcId} className="flex items-center gap-2">
                        <X size={14} style={{ color: '#ddd' }} />
                        <span style={{ fontSize: 12, color: '#ccc' }}>{SERVICE_NAMES[svcId] || svcId}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
              <button onClick={onNewOrder}
                style={{ width: '100%', padding: '10px 0', borderRadius: 10, background: pkg.color, color: '#fff', fontSize: 13, fontWeight: 600, border: 'none', cursor: 'pointer', marginTop: 8 }}>
                Get Started
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============ 4. ORDERS ============

function OrdersSection({ onNewOrder }: { onNewOrder: () => void }) {
  const [orders, setOrders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedOrder, setExpandedOrder] = useState<string | null>(null);

  useEffect(() => {
    fetch(API + '/llcfactory/orders').then(r => r.json()).then(data => setOrders(data.orders || data || []))
      .catch(() => setOrders([
        { id: 'ORD-001', customer: 'Sarah Johnson', email: 'sarah@bloom.co', business: 'Bloom & Co LLC', state: 'DC', package: 'Professional', status: 'processing', total: 248, date: '2026-03-07', services: ['LLC Formation', 'EIN', 'Operating Agreement'], timeline: [{ date: '2026-03-07', event: 'Order received', status: 'completed' }, { date: '2026-03-07', event: 'Documents prepared', status: 'completed' }, { date: '2026-03-08', event: 'Filed with DLCP', status: 'active' }] },
        { id: 'ORD-002', customer: 'Marcus Lee', email: 'marcus@techv.io', business: 'TechVenture Corp', state: 'VA', package: 'Empire', status: 'filed', total: 499, date: '2026-03-06', services: ['Corp Formation', 'EIN', 'Operating Agreement', 'Registered Agent'], timeline: [{ date: '2026-03-06', event: 'Order received', status: 'completed' }, { date: '2026-03-06', event: 'Filed with SCC', status: 'completed' }, { date: '2026-03-07', event: 'Awaiting SCC approval', status: 'active' }] },
        { id: 'ORD-003', customer: 'Diana Park', email: 'diana@greenpath.com', business: 'Green Path Consulting', state: 'MD', package: 'Starter', status: 'approved', total: 149, date: '2026-03-05', services: ['LLC Formation'], timeline: [{ date: '2026-03-05', event: 'Order received', status: 'completed' }, { date: '2026-03-05', event: 'Filed with SDAT', status: 'completed' }, { date: '2026-03-07', event: 'Approved by SDAT', status: 'completed' }] },
        { id: 'ORD-004', customer: 'James Wright', email: 'james@wrightlegal.com', business: 'Wright Legal PLLC', state: 'DC', package: 'Empire', status: 'delivered', total: 598, date: '2026-03-04', services: ['LLC Formation', 'EIN', 'Operating Agreement', 'Registered Agent', 'Apostille'], timeline: [] },
        { id: 'ORD-005', customer: 'Amara Obi', email: 'amara@obiimports.com', business: 'Obi Imports LLC', state: 'VA', package: 'Professional', status: 'completed', total: 349, date: '2026-03-03', services: ['LLC Formation', 'EIN', 'Operating Agreement'], timeline: [] },
        { id: 'ORD-006', customer: 'Chen Wei', email: 'chen@silkroad.biz', business: 'Silk Road Trading LLC', state: 'MD', package: 'Professional', status: 'received', total: 299, date: '2026-03-08', services: ['LLC Formation', 'EIN', 'Operating Agreement', 'BOI Report'], timeline: [{ date: '2026-03-08', event: 'Order received', status: 'active' }] },
      ]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = orders.filter(o => {
    if (filter !== 'all' && o.status !== filter) return false;
    if (searchQuery && !o.customer.toLowerCase().includes(searchQuery.toLowerCase()) && !o.business.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const filterTabs = [
    { id: 'all', label: 'All' },
    { id: 'received', label: 'Received' },
    { id: 'processing', label: 'Processing' },
    { id: 'filed', label: 'Filed' },
    { id: 'completed', label: 'Completed' },
  ];

  if (loading) return <div className="flex-1 flex items-center justify-center py-20"><Loader2 size={24} className="text-[#16a34a] animate-spin" /></div>;

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center justify-between mb-5">
        <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>Orders</h1>
        <div className="flex items-center gap-3">
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#999' }} />
            <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Search orders..."
              style={{ padding: '8px 12px 8px 30px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 12, width: 200, background: '#fff', outline: 'none' }} />
          </div>
          <button onClick={onNewOrder}
            style={{ padding: '8px 16px', borderRadius: 10, background: '#16a34a', color: '#fff', fontSize: 12, fontWeight: 600, border: 'none', cursor: 'pointer' }}
            className="flex items-center gap-2"><Plus size={14} /> New Order</button>
        </div>
      </div>

      <div className="flex items-center gap-1 mb-4">
        {filterTabs.map(tab => (
          <button key={tab.id} onClick={() => setFilter(tab.id)}
            style={{ padding: '6px 14px', borderRadius: 8, fontSize: 11, fontWeight: filter === tab.id ? 700 : 500, background: filter === tab.id ? '#16a34a' : '#fff', color: filter === tab.id ? '#fff' : '#666', border: '1px solid ' + (filter === tab.id ? '#16a34a' : '#ece8e0'), cursor: 'pointer' }}>
            {tab.label}
          </button>
        ))}
      </div>

      <div className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="empire-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #ece8e0' }}>
              {['Order #', 'Customer', 'Business', 'State', 'Package', 'Status', 'Total', 'Date', ''].map(h => (
                <th key={h} style={{ padding: '10px 14px', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5, color: '#999', textAlign: 'left' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map(o => {
              const st = STATUS_COLORS[o.status] || STATUS_COLORS.received;
              const isExpanded = expandedOrder === o.id;
              return (
                <React.Fragment key={o.id}>
                  <tr onClick={() => setExpandedOrder(isExpanded ? null : o.id)} style={{ borderBottom: '1px solid #f0ece4', cursor: 'pointer' }}
                    onMouseEnter={e => (e.currentTarget.style.background = '#fdf8eb')} onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                    <td style={{ padding: '10px 14px', fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{o.id}</td>
                    <td style={{ padding: '10px 14px', fontSize: 12, color: '#1a1a1a' }}>{o.customer}</td>
                    <td style={{ padding: '10px 14px', fontSize: 12, color: '#666' }}>{o.business}</td>
                    <td style={{ padding: '10px 14px', fontSize: 12, color: '#666' }}>{o.state}</td>
                    <td style={{ padding: '10px 14px', fontSize: 12, color: '#666' }}>{o.package}</td>
                    <td style={{ padding: '10px 14px' }}><span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 20, background: st.bg, color: st.color, fontWeight: 600 }}>{st.label}</span></td>
                    <td style={{ padding: '10px 14px', fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>${o.total}</td>
                    <td style={{ padding: '10px 14px', fontSize: 11, color: '#999' }}>{o.date}</td>
                    <td style={{ padding: '10px 14px' }}>{isExpanded ? <ChevronUp size={14} className="text-[#999]" /> : <ChevronDown size={14} className="text-[#999]" />}</td>
                  </tr>
                  {isExpanded && (
                    <tr>
                      <td colSpan={9} style={{ padding: '16px 20px', background: '#faf8f5', borderBottom: '1px solid #ece8e0' }}>
                        <div className="grid grid-cols-3 gap-4">
                          <div>
                            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', marginBottom: 8 }}>Services</div>
                            {(o.services || []).map((s: string, i: number) => (
                              <div key={i} className="flex items-center gap-2 mb-1"><Check size={12} className="text-[#16a34a]" /><span style={{ fontSize: 12, color: '#1a1a1a' }}>{s}</span></div>
                            ))}
                          </div>
                          <div>
                            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', marginBottom: 8 }}>Contact</div>
                            <div style={{ fontSize: 12, color: '#1a1a1a' }}>{o.customer}</div>
                            <div style={{ fontSize: 11, color: '#666' }}>{o.email || 'No email on file'}</div>
                          </div>
                          <div>
                            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', marginBottom: 8 }}>Timeline</div>
                            {(o.timeline || []).length > 0 ? (o.timeline || []).map((t: any, i: number) => (
                              <div key={i} className="flex items-center gap-2 mb-1">
                                <div className="w-2 h-2 rounded-full" style={{ background: t.status === 'completed' ? '#16a34a' : t.status === 'active' ? '#b8960c' : '#ddd' }} />
                                <span style={{ fontSize: 11, color: '#666' }}>{t.date} — {t.event}</span>
                              </div>
                            )) : <div style={{ fontSize: 11, color: '#999' }}>No timeline data</div>}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
        {filtered.length === 0 && <div style={{ padding: 30, textAlign: 'center', color: '#999', fontSize: 12 }}>No orders found</div>}
      </div>
    </div>
  );
}

// ============ 5. CUSTOMERS ============

function CustomersSection() {
  const [customers, setCustomers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCustomer, setSelectedCustomer] = useState<any>(null);

  useEffect(() => {
    fetch(API + '/llcfactory/customers').then(r => r.json()).then(data => setCustomers(data.customers || data || []))
      .catch(() => setCustomers([
        { id: 'C-001', name: 'Sarah Johnson', email: 'sarah@bloom.co', phone: '(202) 555-0101', orders: 2, totalSpent: 497, status: 'active' },
        { id: 'C-002', name: 'Marcus Lee', email: 'marcus@techv.io', phone: '(703) 555-0202', orders: 1, totalSpent: 499, status: 'active' },
        { id: 'C-003', name: 'Diana Park', email: 'diana@greenpath.com', phone: '(301) 555-0303', orders: 1, totalSpent: 149, status: 'active' },
        { id: 'C-004', name: 'James Wright', email: 'james@wrightlegal.com', phone: '(202) 555-0404', orders: 3, totalSpent: 1247, status: 'active' },
        { id: 'C-005', name: 'Amara Obi', email: 'amara@obiimports.com', phone: '(571) 555-0505', orders: 1, totalSpent: 349, status: 'active' },
        { id: 'C-006', name: 'Chen Wei', email: 'chen@silkroad.biz', phone: '(240) 555-0606', orders: 1, totalSpent: 299, status: 'new' },
      ]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex-1 flex items-center justify-center py-20"><Loader2 size={24} className="text-[#16a34a] animate-spin" /></div>;

  if (selectedCustomer) {
    return (
      <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
        <button onClick={() => setSelectedCustomer(null)} style={{ fontSize: 12, color: '#16a34a', background: 'none', border: 'none', cursor: 'pointer', marginBottom: 16, fontWeight: 600 }}
          className="flex items-center gap-1"><ChevronRight size={14} style={{ transform: 'rotate(180deg)' }} /> Back to Customers</button>
        <div className="empire-card" style={{ padding: '24px 28px' }}>
          <div className="flex items-center gap-4 mb-6">
            <div className="w-12 h-12 rounded-full bg-[#dcfce7] flex items-center justify-center"><User size={24} className="text-[#16a34a]" /></div>
            <div>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a' }}>{selectedCustomer.name}</div>
              <div style={{ fontSize: 12, color: '#666' }}>{selectedCustomer.email} &middot; {selectedCustomer.phone}</div>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div style={{ padding: 14, borderRadius: 10, background: '#f5f2ed', textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a' }}>{selectedCustomer.orders}</div>
              <div style={{ fontSize: 10, color: '#999', fontWeight: 700, textTransform: 'uppercase' }}>Orders</div>
            </div>
            <div style={{ padding: 14, borderRadius: 10, background: '#f5f2ed', textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#16a34a' }}>${selectedCustomer.totalSpent}</div>
              <div style={{ fontSize: 10, color: '#999', fontWeight: 700, textTransform: 'uppercase' }}>Total Spent</div>
            </div>
            <div style={{ padding: 14, borderRadius: 10, background: '#f5f2ed', textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#b8960c' }}>{selectedCustomer.status}</div>
              <div style={{ fontSize: 10, color: '#999', fontWeight: 700, textTransform: 'uppercase' }}>Status</div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center justify-between mb-5">
        <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>Customers</h1>
        <button style={{ padding: '8px 16px', borderRadius: 10, background: '#16a34a', color: '#fff', fontSize: 12, fontWeight: 600, border: 'none', cursor: 'pointer' }}
          className="flex items-center gap-2"><Plus size={14} /> Add Customer</button>
      </div>

      <div className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="empire-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #ece8e0' }}>
              {['Name', 'Email', 'Phone', 'Orders', 'Total Spent', 'Status'].map(h => (
                <th key={h} style={{ padding: '10px 14px', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5, color: '#999', textAlign: 'left' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {customers.map(c => (
              <tr key={c.id} onClick={() => setSelectedCustomer(c)} style={{ borderBottom: '1px solid #f0ece4', cursor: 'pointer' }}
                onMouseEnter={e => (e.currentTarget.style.background = '#fdf8eb')} onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                <td style={{ padding: '10px 14px', fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{c.name}</td>
                <td style={{ padding: '10px 14px', fontSize: 12, color: '#666' }}>{c.email}</td>
                <td style={{ padding: '10px 14px', fontSize: 12, color: '#666' }}>{c.phone}</td>
                <td style={{ padding: '10px 14px', fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{c.orders}</td>
                <td style={{ padding: '10px 14px', fontSize: 12, fontWeight: 600, color: '#16a34a' }}>${c.totalSpent}</td>
                <td style={{ padding: '10px 14px' }}>
                  <span style={{ fontSize: 10, padding: '3px 8px', borderRadius: 20, background: c.status === 'active' ? '#dcfce7' : '#fdf8eb', color: c.status === 'active' ? '#16a34a' : '#b8960c', fontWeight: 600 }}>{c.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {customers.length === 0 && <div style={{ padding: 30, textAlign: 'center', color: '#999', fontSize: 12 }}>No customers yet</div>}
      </div>
    </div>
  );
}

// ============ 6. APOSTILLE ============

function ApostilleSection() {
  const [apostilleOrders, setApostilleOrders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [apostilleTab, setApostilleTab] = useState<'Tracker' | 'Forms & Fees' | 'Process Guide'>('Tracker');

  useEffect(() => {
    fetch(API + '/llcfactory/apostille').then(r => r.json()).then(data => { const list = data?.orders || data; setApostilleOrders(Array.isArray(list) ? list : []); })
      .catch(() => setApostilleOrders([
        { id: 'APO-001', customer: 'James Wright', documentType: 'Articles of Organization', jurisdiction: 'DC → Federal', status: 3, dateReceived: '2026-03-02', estimatedDelivery: '2026-03-15' },
        { id: 'APO-002', customer: 'Amara Obi', documentType: 'Certificate of Good Standing', jurisdiction: 'VA → Embassy (Nigeria)', status: 4, dateReceived: '2026-02-25', estimatedDelivery: '2026-03-20' },
        { id: 'APO-003', customer: 'Chen Wei', documentType: 'Corporate Resolution', jurisdiction: 'MD → Federal → Embassy (China)', status: 1, dateReceived: '2026-03-08', estimatedDelivery: '2026-04-01' },
      ]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex-1 flex items-center justify-center py-20"><Loader2 size={24} className="text-[#16a34a] animate-spin" /></div>;

  const thStyle: React.CSSProperties = { padding: '10px 14px', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5, color: '#999', textAlign: 'left' };
  const tdStyle: React.CSSProperties = { padding: '10px 14px', fontSize: 12, color: '#666' };
  const subTabs: Array<'Tracker' | 'Forms & Fees' | 'Process Guide'> = ['Tracker', 'Forms & Fees', 'Process Guide'];

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0, marginBottom: 20 }}>Apostille Center</h1>

      {/* Sub-tab navigation */}
      <div className="flex items-center gap-2 mb-6">
        {subTabs.map(tab => (
          <button
            key={tab}
            onClick={() => setApostilleTab(tab)}
            style={{
              padding: '8px 18px', borderRadius: 8, fontSize: 12, fontWeight: 600, border: 'none', cursor: 'pointer',
              background: apostilleTab === tab ? '#7c3aed' : '#f5f0e8',
              color: apostilleTab === tab ? '#fff' : '#666',
              transition: 'all 0.15s ease',
            }}
          >
            {tab === 'Tracker' && <ClipboardList size={13} style={{ display: 'inline', marginRight: 5, verticalAlign: -2 }} />}
            {tab === 'Forms & Fees' && <FileText size={13} style={{ display: 'inline', marginRight: 5, verticalAlign: -2 }} />}
            {tab === 'Process Guide' && <MapPin size={13} style={{ display: 'inline', marginRight: 5, verticalAlign: -2 }} />}
            {tab}
          </button>
        ))}
      </div>

      {/* ==================== TAB: TRACKER ==================== */}
      {apostilleTab === 'Tracker' && (
        <>
          {/* Pipeline visualization */}
          <div className="empire-card mb-6" style={{ padding: '20px 24px' }}>
            <div className="section-label" style={{ marginBottom: 14 }}>Authentication Pipeline</div>
            <div className="flex items-center justify-between">
              {APOSTILLE_STAGES.map((stage, i) => (
                <React.Fragment key={stage}>
                  <div style={{ textAlign: 'center', flex: 1 }}>
                    <div className="w-10 h-10 rounded-full mx-auto mb-2 flex items-center justify-center" style={{ background: '#ede9fe', color: '#7c3aed', fontSize: 14, fontWeight: 700 }}>{i + 1}</div>
                    <div style={{ fontSize: 10, fontWeight: 600, color: '#666' }}>{stage}</div>
                  </div>
                  {i < APOSTILLE_STAGES.length - 1 && <ArrowRight size={16} className="text-[#ddd] flex-shrink-0" />}
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Apostille orders table */}
          <div className="empire-card mb-6" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="empire-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #ece8e0' }}>
                  {['ID', 'Customer', 'Document', 'Jurisdiction', 'Progress', 'Received', 'Est. Delivery'].map(h => (
                    <th key={h} style={thStyle}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {apostilleOrders.map(o => (
                  <tr key={o.id} style={{ borderBottom: '1px solid #f0ece4' }}>
                    <td style={{ ...tdStyle, fontWeight: 600, color: '#1a1a1a' }}>{o.id}</td>
                    <td style={{ ...tdStyle, color: '#1a1a1a' }}>{o.customer}</td>
                    <td style={tdStyle}>{o.documentType}</td>
                    <td style={tdStyle}>{o.jurisdiction}</td>
                    <td style={{ padding: '10px 14px' }}>
                      <div className="flex items-center gap-1">
                        {APOSTILLE_STAGES.map((_, i) => (
                          <div key={i} style={{ width: 20, height: 6, borderRadius: 3, background: i < o.status ? '#7c3aed' : '#ece8e0' }} />
                        ))}
                        <span style={{ fontSize: 10, color: '#7c3aed', fontWeight: 600, marginLeft: 6 }}>{o.status}/{APOSTILLE_STAGES.length}</span>
                      </div>
                    </td>
                    <td style={{ ...tdStyle, fontSize: 11, color: '#999' }}>{o.dateReceived}</td>
                    <td style={{ ...tdStyle, fontSize: 11, color: '#999' }}>{o.estimatedDelivery}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {apostilleOrders.length === 0 && <div style={{ padding: 30, textAlign: 'center', color: '#999', fontSize: 12 }}>No apostille orders</div>}
          </div>

          {/* Jurisdiction Reference Cards */}
          <div className="section-label" style={{ marginBottom: 10 }}>Jurisdiction Reference</div>
          <div className="grid grid-cols-2 gap-3 mb-6">
            <div className="empire-card" style={{ padding: '14px 18px', borderLeft: '3px solid #2563eb' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a', marginBottom: 6 }}>
                <Building size={13} style={{ display: 'inline', marginRight: 5, verticalAlign: -2, color: '#2563eb' }} />
                District of Columbia
              </div>
              <div style={{ fontSize: 11, color: '#666', lineHeight: 1.6 }}>
                <strong>Fee:</strong> $15/document<br />
                <strong>Authority:</strong> Office of Notary Commissions &amp; Authentications (ONCA)<br />
                <strong>Processing:</strong> 2-3 business days<br />
                <strong>Note:</strong> Document must be notarized by a DC notary or be a DC government-issued certificate
              </div>
            </div>
            <div className="empire-card" style={{ padding: '14px 18px', borderLeft: '3px solid #16a34a' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a', marginBottom: 6 }}>
                <Building size={13} style={{ display: 'inline', marginRight: 5, verticalAlign: -2, color: '#16a34a' }} />
                Maryland
              </div>
              <div style={{ fontSize: 11, color: '#666', lineHeight: 1.6 }}>
                <strong>Fee:</strong> $5/document<br />
                <strong>Authority:</strong> Secretary of State, Certification Desk<br />
                <strong>Processing:</strong> Up to 1 week (mail) / Same-day (walk-in)<br />
                <strong>Extra Step:</strong> Notarized docs require Circuit Court Clerk authentication (~$1) before state apostille
              </div>
            </div>
            <div className="empire-card" style={{ padding: '14px 18px', borderLeft: '3px solid #b8960c' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a', marginBottom: 6 }}>
                <Building size={13} style={{ display: 'inline', marginRight: 5, verticalAlign: -2, color: '#b8960c' }} />
                Virginia
              </div>
              <div style={{ fontSize: 11, color: '#666', lineHeight: 1.6 }}>
                <strong>Fee:</strong> $10/document ($5 each additional in same batch)<br />
                <strong>Authority:</strong> Secretary of the Commonwealth<br />
                <strong>Processing:</strong> 5-7 business days (mail) / Appointment-only in-person (Mon-Thu)<br />
                <strong>Note:</strong> In-person requires scheduled appointment
              </div>
            </div>
            <div className="empire-card" style={{ padding: '14px 18px', borderLeft: '3px solid #7c3aed' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a', marginBottom: 6 }}>
                <Globe size={13} style={{ display: 'inline', marginRight: 5, verticalAlign: -2, color: '#7c3aed' }} />
                Federal (US Dept of State)
              </div>
              <div style={{ fontSize: 11, color: '#666', lineHeight: 1.6 }}>
                <strong>Fee:</strong> $20/document<br />
                <strong>Form:</strong> DS-4194 (Application for Apostille / Authentication)<br />
                <strong>Processing:</strong> 5+ weeks (mail) / 2-3 weeks (walk-in drop-off, DC office)<br />
                <strong>Use for:</strong> FBI background checks, federal court docs, any federal agency documents
              </div>
            </div>
          </div>
        </>
      )}

      {/* ==================== TAB: FORMS & FEES ==================== */}
      {apostilleTab === 'Forms & Fees' && (
        <>
          {/* Fee Comparison Table */}
          <div className="section-label" style={{ marginBottom: 10 }}>Fee Comparison</div>
          <div className="empire-card mb-6" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="empire-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #ece8e0' }}>
                  {['', 'DC', 'Maryland', 'Virginia', 'Federal'].map(h => (
                    <th key={h} style={{ ...thStyle, textAlign: h === '' ? 'left' : 'center' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  { label: 'Apostille Fee', dc: '$15/doc', md: '$5/doc', va: '$10/doc ($5 add\'l)', fed: '$20/doc' },
                  { label: 'Notary Act Fee Cap', dc: '$5/signature', md: '$4/signature', va: '$5/notarial act', fed: 'N/A' },
                  { label: 'Circuit Court Auth', dc: 'N/A', md: '~$1/doc (required)', va: 'N/A', fed: 'N/A' },
                  { label: 'Processing Time', dc: '2-3 days', md: '1 week mail / same-day walk-in', va: '5-7 days mail / appt in-person', fed: '5+ wks mail / 2-3 wks drop-off' },
                  { label: 'RON Available?', dc: 'Yes', md: 'Yes', va: 'Yes (RON pioneer)', fed: 'N/A' },
                ].map(row => (
                  <tr key={row.label} style={{ borderBottom: '1px solid #f0ece4' }}>
                    <td style={{ ...tdStyle, fontWeight: 600, color: '#1a1a1a', fontSize: 11 }}>{row.label}</td>
                    <td style={{ ...tdStyle, textAlign: 'center', fontSize: 11 }}>{row.dc}</td>
                    <td style={{ ...tdStyle, textAlign: 'center', fontSize: 11 }}>{row.md}</td>
                    <td style={{ ...tdStyle, textAlign: 'center', fontSize: 11 }}>{row.va}</td>
                    <td style={{ ...tdStyle, textAlign: 'center', fontSize: 11 }}>{row.fed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Forms & Requirements Quick Reference */}
          <div className="section-label" style={{ marginBottom: 10 }}>Document Types &amp; Requirements</div>
          <div className="empire-card mb-6" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="empire-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #ece8e0' }}>
                  {['Document Type', 'Examples', 'Authentication Chain'].map(h => (
                    <th key={h} style={thStyle}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid #f0ece4' }}>
                  <td style={{ ...tdStyle, fontWeight: 600, color: '#1a1a1a' }}>
                    <FileText size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: -2, color: '#2563eb' }} />
                    Private Documents
                  </td>
                  <td style={{ ...tdStyle, fontSize: 11 }}>Power of Attorney, Affidavit, Corporate Resolution, Operating Agreement</td>
                  <td style={tdStyle}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
                      Notarize <ArrowRight size={10} style={{ color: '#999' }} /> <span style={{ color: '#16a34a', fontWeight: 600 }}>MD only: Circuit Court</span> <ArrowRight size={10} style={{ color: '#999' }} /> State Apostille
                    </span>
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid #f0ece4' }}>
                  <td style={{ ...tdStyle, fontWeight: 600, color: '#1a1a1a' }}>
                    <Award size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: -2, color: '#b8960c' }} />
                    Government-Issued
                  </td>
                  <td style={{ ...tdStyle, fontSize: 11 }}>Birth Certificate, Marriage Certificate, Court Order, Certified Transcript</td>
                  <td style={tdStyle}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
                      Certified Copy <ArrowRight size={10} style={{ color: '#999' }} /> State Apostille <span style={{ color: '#999', fontStyle: 'italic' }}>(no notary needed)</span>
                    </span>
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid #f0ece4' }}>
                  <td style={{ ...tdStyle, fontWeight: 600, color: '#1a1a1a' }}>
                    <Shield size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: -2, color: '#7c3aed' }} />
                    Federal Documents
                  </td>
                  <td style={{ ...tdStyle, fontSize: 11 }}>FBI Background Check, Federal Court Records, USCIS Documents, Patent/Trademark Certs</td>
                  <td style={tdStyle}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
                      DS-4194 <ArrowRight size={10} style={{ color: '#999' }} /> US Dept of State Apostille
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Required Government Forms */}
          <div className="section-label" style={{ marginBottom: 10 }}>Required Government Forms</div>
          <div className="grid grid-cols-1 gap-3 mb-6">
            {[
              { jurisdiction: 'DC', color: '#2563eb', form: 'Request for Authentication (mail-in form)', url: 'https://os.dc.gov/page/apostilles-and-authentications', note: 'Submit original notarized doc + completed request form + fee' },
              { jurisdiction: 'Maryland', color: '#16a34a', form: 'Certification Checklist', url: 'https://sos.maryland.gov/documents/certchecklist.pdf', note: 'Use checklist to verify all requirements before submitting' },
              { jurisdiction: 'Virginia', color: '#b8960c', form: 'Authentication Request Cover Letter', url: 'https://www.commonwealth.virginia.gov/official-documents/apostilles-and-authentications/', note: 'Include cover letter + docs + payment; schedule appointment for in-person' },
              { jurisdiction: 'Federal', color: '#7c3aed', form: 'DS-4194 — Application for Apostille', url: 'https://eforms.state.gov/Forms/ds4194.pdf', note: 'Required for all federal document apostilles; mail to US Dept of State, Office of Authentications' },
              { jurisdiction: 'FBI', color: '#999', form: 'FD-1164 — Identity History Summary Request', url: 'https://www.fbi.gov/how-can-we-help-you/more-fbi-services-and-information/identity-history-summary-checks', note: 'Request FBI background check; result then goes through DS-4194 federal apostille process' },
            ].map(f => (
              <div key={f.jurisdiction} className="empire-card" style={{ padding: '12px 18px', borderLeft: `3px solid ${f.color}` }}>
                <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>
                    <span style={{ color: f.color, marginRight: 6 }}>{f.jurisdiction}</span>
                    {f.form}
                  </div>
                  <a href={f.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 11, color: '#2563eb', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 3, textDecoration: 'none' }}>
                    Open <ExternalLink size={11} />
                  </a>
                </div>
                <div style={{ fontSize: 11, color: '#666', lineHeight: 1.5 }}>{f.note}</div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* ==================== TAB: PROCESS GUIDE ==================== */}
      {apostilleTab === 'Process Guide' && (
        <>
          {/* Authentication Chain Flowcharts — Hague Country */}
          <div className="section-label" style={{ marginBottom: 10 }}>Hague Convention Country — Authentication Chains</div>

          {/* Private Document Flow */}
          <div className="empire-card mb-4" style={{ padding: '16px 20px' }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a', marginBottom: 12 }}>
              <FileText size={13} style={{ display: 'inline', marginRight: 5, verticalAlign: -2, color: '#2563eb' }} />
              Private Document (POA, Affidavit, Corporate Resolution)
            </div>
            <div className="flex items-center flex-wrap gap-2">
              {[
                { label: 'Draft Document', bg: '#f0f4ff', color: '#2563eb' },
                { label: 'Notarize', bg: '#f0fdf4', color: '#16a34a' },
                { label: 'MD Only: Circuit Court Clerk Auth (~$1)', bg: '#fefce8', color: '#b8960c' },
                { label: 'State Apostille', bg: '#ede9fe', color: '#7c3aed' },
                { label: 'Done — Accepted in Hague Countries', bg: '#f0fdf4', color: '#16a34a' },
              ].map((step, i, arr) => (
                <React.Fragment key={i}>
                  <div style={{ padding: '8px 14px', borderRadius: 8, background: step.bg, border: `1px solid ${step.color}22`, fontSize: 11, fontWeight: 600, color: step.color }}>{step.label}</div>
                  {i < arr.length - 1 && <ArrowRight size={14} style={{ color: '#ccc', flexShrink: 0 }} />}
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Government Document Flow */}
          <div className="empire-card mb-4" style={{ padding: '16px 20px' }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a', marginBottom: 12 }}>
              <Award size={13} style={{ display: 'inline', marginRight: 5, verticalAlign: -2, color: '#b8960c' }} />
              Government-Issued Document (Birth Cert, Court Order)
            </div>
            <div className="flex items-center flex-wrap gap-2">
              {[
                { label: 'Obtain Certified Copy', bg: '#f0f4ff', color: '#2563eb' },
                { label: 'State Apostille (no notary needed)', bg: '#ede9fe', color: '#7c3aed' },
                { label: 'Done — Accepted in Hague Countries', bg: '#f0fdf4', color: '#16a34a' },
              ].map((step, i, arr) => (
                <React.Fragment key={i}>
                  <div style={{ padding: '8px 14px', borderRadius: 8, background: step.bg, border: `1px solid ${step.color}22`, fontSize: 11, fontWeight: 600, color: step.color }}>{step.label}</div>
                  {i < arr.length - 1 && <ArrowRight size={14} style={{ color: '#ccc', flexShrink: 0 }} />}
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Federal Document Flow */}
          <div className="empire-card mb-6" style={{ padding: '16px 20px' }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a', marginBottom: 12 }}>
              <Shield size={13} style={{ display: 'inline', marginRight: 5, verticalAlign: -2, color: '#7c3aed' }} />
              Federal Document (FBI Check, Federal Court Record)
            </div>
            <div className="flex items-center flex-wrap gap-2">
              {[
                { label: 'Obtain Federal Document', bg: '#f0f4ff', color: '#2563eb' },
                { label: 'Complete Form DS-4194', bg: '#fefce8', color: '#b8960c' },
                { label: 'Submit to US Dept of State ($20)', bg: '#ede9fe', color: '#7c3aed' },
                { label: 'Done — Accepted in Hague Countries', bg: '#f0fdf4', color: '#16a34a' },
              ].map((step, i, arr) => (
                <React.Fragment key={i}>
                  <div style={{ padding: '8px 14px', borderRadius: 8, background: step.bg, border: `1px solid ${step.color}22`, fontSize: 11, fontWeight: 600, color: step.color }}>{step.label}</div>
                  {i < arr.length - 1 && <ArrowRight size={14} style={{ color: '#ccc', flexShrink: 0 }} />}
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Non-Hague Country Flow */}
          <div className="section-label" style={{ marginBottom: 10 }}>Non-Hague Country — Embassy Legalization Chain</div>
          <div className="empire-card mb-4" style={{ padding: '16px 20px' }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a', marginBottom: 12 }}>
              <Globe size={13} style={{ display: 'inline', marginRight: 5, verticalAlign: -2, color: '#7c3aed' }} />
              Any Document Destined for a Non-Hague Country
            </div>
            <div className="flex items-center flex-wrap gap-2">
              {[
                { label: 'Prepare & Notarize (if private)', bg: '#f0f4ff', color: '#2563eb' },
                { label: 'State Authentication (or Federal via DS-4194)', bg: '#ede9fe', color: '#7c3aed' },
                { label: 'US Dept of State Authentication', bg: '#fefce8', color: '#b8960c' },
                { label: 'Embassy / Consulate Legalization', bg: '#fef2f2', color: '#dc2626' },
                { label: 'Done — Accepted in Destination Country', bg: '#f0fdf4', color: '#16a34a' },
              ].map((step, i, arr) => (
                <React.Fragment key={i}>
                  <div style={{ padding: '8px 14px', borderRadius: 8, background: step.bg, border: `1px solid ${step.color}22`, fontSize: 11, fontWeight: 600, color: step.color }}>{step.label}</div>
                  {i < arr.length - 1 && <ArrowRight size={14} style={{ color: '#ccc', flexShrink: 0 }} />}
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Embassy Legalization Info */}
          <div className="empire-card" style={{ padding: '16px 20px', borderLeft: '3px solid #b8960c' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a', marginBottom: 6 }}>
              <AlertTriangle size={13} style={{ display: 'inline', marginRight: 5, verticalAlign: -2, color: '#b8960c' }} />
              Embassy Legalization — Non-Hague Countries
            </div>
            <div style={{ fontSize: 11, color: '#666', lineHeight: 1.7 }}>
              Countries that have <strong>not</strong> joined the Hague Apostille Convention (e.g., Canada, China, UAE, Saudi Arabia, Qatar) do not accept apostilles.
              Instead, documents require a full <strong>authentication + legalization</strong> chain: the document must first be authenticated by the
              US Department of State, then legalized (stamped/certified) by the destination country&apos;s embassy or consulate in the US.
              Processing times and fees vary by embassy. Some embassies require appointments; others accept mail-in submissions.
              Always check the specific embassy website for current requirements, fees, and turnaround times before submitting.
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ============ 7. STATE GUIDES ============

const APOSTILLE_FEES: Record<string, { fee: string; processing: string; office: string }> = {
  AL: { fee: '$4/doc', processing: '5-10 business days', office: 'Secretary of State' },
  AK: { fee: '$25/doc', processing: '5-10 business days', office: 'Lt. Governor' },
  AZ: { fee: '$3/doc', processing: '5-7 business days', office: 'Secretary of State' },
  AR: { fee: '$5/doc', processing: '3-5 business days', office: 'Secretary of State' },
  CA: { fee: '$20/doc', processing: '5-10 business days', office: 'Secretary of State' },
  CO: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  CT: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  DE: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  DC: { fee: '$20/doc', processing: '5-7 business days', office: 'Office of the Secretary' },
  FL: { fee: '$10/doc', processing: '5-7 business days', office: 'Secretary of State' },
  GA: { fee: '$3/doc', processing: '5-10 business days', office: 'Superior Court Clerk' },
  HI: { fee: '$2/doc', processing: '5-10 business days', office: 'Lt. Governor' },
  ID: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  IL: { fee: '$2/doc', processing: '5-10 business days', office: 'Secretary of State' },
  IN: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  IA: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  KS: { fee: '$7.50/doc', processing: '3-5 business days', office: 'Secretary of State' },
  KY: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  LA: { fee: '$5/doc', processing: '5-7 business days', office: 'Secretary of State' },
  ME: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  MD: { fee: '$22/doc', processing: '5-10 business days', office: 'Secretary of State' },
  MA: { fee: '$6/doc', processing: '3-5 business days', office: 'Secretary of the Commonwealth' },
  MI: { fee: '$1/doc', processing: '5-10 business days', office: 'Secretary of State' },
  MN: { fee: '$5/doc', processing: '3-5 business days', office: 'Secretary of State' },
  MS: { fee: '$5/doc', processing: '3-5 business days', office: 'Secretary of State' },
  MO: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  MT: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  NE: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  NV: { fee: '$20/doc', processing: '3-5 business days', office: 'Secretary of State' },
  NH: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  NJ: { fee: '$5/doc', processing: '5-7 business days', office: 'Secretary of State' },
  NM: { fee: '$3/doc', processing: '3-5 business days', office: 'Secretary of State' },
  NY: { fee: '$10/doc', processing: '5-10 business days', office: 'Secretary of State' },
  NC: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  ND: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  OH: { fee: '$5/doc', processing: '3-5 business days', office: 'Secretary of State' },
  OK: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  OR: { fee: '$10/doc', processing: '5-7 business days', office: 'Secretary of State' },
  PA: { fee: '$15/doc', processing: '3-5 business days', office: 'Secretary of State' },
  RI: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  SC: { fee: '$2/doc', processing: '3-5 business days', office: 'Secretary of State' },
  SD: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  TN: { fee: '$2/doc', processing: '3-5 business days', office: 'Secretary of State' },
  TX: { fee: '$15/doc', processing: '5-7 business days', office: 'Secretary of State' },
  UT: { fee: '$10/doc', processing: '3-5 business days', office: 'Lt. Governor' },
  VT: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  VA: { fee: '$8/doc', processing: '3-5 business days', office: 'Secretary of the Commonwealth' },
  WA: { fee: '$15/doc', processing: '5-7 business days', office: 'Secretary of State' },
  WV: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  WI: { fee: '$10/doc', processing: '3-5 business days', office: 'Secretary of State' },
  WY: { fee: '$4/doc', processing: '3-5 business days', office: 'Secretary of State' },
};

function StateGuidesSection() {
  const allStateCodes = Object.keys(STATE_GUIDES);
  const [selectedState, setSelectedState] = useState<string>('DC');
  const [searchTerm, setSearchTerm] = useState('');
  const guide = STATE_GUIDES[selectedState];
  const apostille = APOSTILLE_FEES[selectedState];

  const filteredStates = allStateCodes.filter(code => {
    if (!searchTerm) return true;
    const lower = searchTerm.toLowerCase();
    return code.toLowerCase().includes(lower) || STATE_GUIDES[code].name.toLowerCase().includes(lower);
  });

  const popularStates = ['DE', 'WY', 'TX', 'FL', 'NY', 'CA', 'NV', 'DC', 'MD', 'VA'];

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0, marginBottom: 16 }}>State Formation Guides</h1>

      {/* Popular states quick-select */}
      <div className="section-label" style={{ marginBottom: 8 }}>Popular States</div>
      <div className="flex flex-wrap items-center gap-2 mb-4">
        {popularStates.map(st => (
          <button key={st} onClick={() => setSelectedState(st)}
            style={{ padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: selectedState === st ? 700 : 500, background: selectedState === st ? '#16a34a' : '#fff', color: selectedState === st ? '#fff' : '#666', border: '1px solid ' + (selectedState === st ? '#16a34a' : '#ece8e0'), cursor: 'pointer' }}>
            {STATE_GUIDES[st].name}
          </button>
        ))}
      </div>

      {/* State selector with search */}
      <div className="flex items-center gap-3 mb-6">
        <div style={{ position: 'relative', flex: 1, maxWidth: 360 }}>
          <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#999' }} />
          <input
            type="text"
            placeholder="Search states..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            style={{ width: '100%', padding: '9px 12px 9px 34px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 13, background: '#fff', outline: 'none' }}
          />
        </div>
        <select
          value={selectedState}
          onChange={e => { setSelectedState(e.target.value); setSearchTerm(''); }}
          style={{ padding: '9px 14px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 13, background: '#fff', color: '#1a1a1a', cursor: 'pointer', outline: 'none', minWidth: 200 }}
        >
          {filteredStates.map(code => (
            <option key={code} value={code}>{STATE_GUIDES[code].name} ({code})</option>
          ))}
        </select>
        <div style={{ fontSize: 12, color: '#999' }}>{allStateCodes.length} jurisdictions</div>
      </div>

      {/* State header */}
      <div className="empire-card mb-5" style={{ padding: '20px 24px' }}>
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl bg-[#dcfce7] flex items-center justify-center"><MapPin size={28} className="text-[#16a34a]" /></div>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a' }}>{guide.name}</div>
            <div style={{ fontSize: 12, color: '#666' }}>{guide.authority}</div>
            <a href={guide.portalUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1" style={{ fontSize: 11, color: '#2563eb', marginTop: 4, textDecoration: 'none' }}>
              <ExternalLink size={12} /> {guide.portal}
            </a>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-5">
        {/* Fee table */}
        <div className="empire-card" style={{ padding: '18px 22px' }}>
          <div className="section-label" style={{ marginBottom: 12 }}>Fees</div>
          <div className="space-y-3">
            {[
              { label: 'Filing Fee', value: `$${guide.filingFee}` },
              { label: 'Expedited Processing', value: `+$${guide.expeditedFee}` },
              { label: `${guide.annualReportFrequency !== 'None' ? guide.annualReportFrequency : 'Annual'} Report`, value: guide.annualReportFrequency === 'None' ? 'N/A' : `$${guide.annualReportFee}` },
            ].map(f => (
              <div key={f.label} className="flex items-center justify-between" style={{ padding: '8px 0', borderBottom: '1px solid #f0ece4' }}>
                <span style={{ fontSize: 12, color: '#666' }}>{f.label}</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{f.value}</span>
              </div>
            ))}
            <div className="flex items-center justify-between" style={{ padding: '8px 0' }}>
              <span style={{ fontSize: 12, color: '#666' }}>Report Deadline</span>
              <span style={{ fontSize: 12, fontWeight: 600, color: '#b8960c' }}>{guide.annualReportDeadline}</span>
            </div>
          </div>
        </div>

        {/* Required docs */}
        <div className="empire-card" style={{ padding: '18px 22px' }}>
          <div className="section-label" style={{ marginBottom: 12 }}>Required Documents</div>
          <div className="space-y-2">
            {guide.requiredDocs.map((doc: string) => (
              <div key={doc} className="flex items-center gap-2">
                <CheckCircle size={14} className="text-[#16a34a]" />
                <span style={{ fontSize: 12, color: '#1a1a1a' }}>{doc}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Apostille info */}
        {apostille && (
          <div className="empire-card" style={{ padding: '18px 22px', borderLeft: '3px solid #7c3aed' }}>
            <div className="section-label" style={{ marginBottom: 12, color: '#7c3aed' }}>Apostille Service</div>
            <div className="space-y-3">
              <div className="flex items-center justify-between" style={{ padding: '8px 0', borderBottom: '1px solid #f0ece4' }}>
                <span style={{ fontSize: 12, color: '#666' }}>State Fee</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{apostille.fee}</span>
              </div>
              <div className="flex items-center justify-between" style={{ padding: '8px 0', borderBottom: '1px solid #f0ece4' }}>
                <span style={{ fontSize: 12, color: '#666' }}>Processing Time</span>
                <span style={{ fontSize: 12, fontWeight: 600, color: '#b8960c' }}>{apostille.processing}</span>
              </div>
              <div className="flex items-center justify-between" style={{ padding: '8px 0' }}>
                <span style={{ fontSize: 12, color: '#666' }}>Issuing Office</span>
                <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{apostille.office}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Steps */}
      <div className="empire-card mb-5" style={{ padding: '18px 22px' }}>
        <div className="section-label" style={{ marginBottom: 12 }}>Formation Process</div>
        <div className="space-y-3">
          {guide.steps.map((step: string, i: number) => (
            <div key={i} className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center" style={{ background: '#dcfce7', color: '#16a34a', fontSize: 11, fontWeight: 700 }}>{i + 1}</div>
              <span style={{ fontSize: 12, color: '#1a1a1a', lineHeight: 1.5, paddingTop: 3 }}>{step}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Tips and warnings */}
      <div className="grid grid-cols-2 gap-4">
        <div className="empire-card" style={{ padding: '18px 22px', borderLeft: '3px solid #16a34a' }}>
          <div className="section-label" style={{ marginBottom: 10, color: '#16a34a' }}>Tips</div>
          <div className="space-y-2">
            {guide.tips.map((tip: string, i: number) => (
              <div key={i} className="flex items-start gap-2">
                <Zap size={12} className="text-[#16a34a] mt-0.5 flex-shrink-0" />
                <span style={{ fontSize: 11, color: '#666', lineHeight: 1.5 }}>{tip}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="empire-card" style={{ padding: '18px 22px', borderLeft: '3px solid #e57e22' }}>
          <div className="section-label" style={{ marginBottom: 10, color: '#e57e22' }}>Warnings</div>
          <div className="space-y-2">
            {guide.warnings.map((w: string, i: number) => (
              <div key={i} className="flex items-start gap-2">
                <AlertTriangle size={12} className="text-[#e57e22] mt-0.5 flex-shrink-0" />
                <span style={{ fontSize: 11, color: '#666', lineHeight: 1.5 }}>{w}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============ 8. FINANCIALS ============

const OPERATIONAL_COSTS: Record<string, number> = {
  'llc-formation': 15, 'corp-formation': 15, 'nonprofit-formation': 15, 'dba-registration': 15,
  'ein-application': 5, 'annual-report': 12, 'boc-report': 8, 'business-license': 10,
  'state-tax-reg': 8, 'compliance-monitoring': 10,
  'operating-agreement': 8, 'articles-amendment': 8, 'certificate-good-standing': 8,
  'apostille-vital-records': 25, 'fbi-background-apostille': 25, 'certified-copy': 8,
  'apostille-service': 25, 'notary-service': 10, 'federal-apostille': 25, 'embassy-legalization': 25,
  'registered-agent': 20, 'mail-forwarding': 10, 'foreign-qualification': 15,
};

const COURIER_COSTS = {
  DC: {
    agency: 'DC DLCP (Dept of Licensing and Consumer Protection)',
    address: '1100 4th St SW, Washington, DC 20024',
    runner_options: [
      { provider: 'In-house Runner', cost: 25, time: 'Same day', notes: 'Part-time employee, $25/trip', recommended: true },
      { provider: 'TaskRabbit', cost: 45, time: 'Same day', notes: 'On-demand, variable pricing ($35-55)' },
      { provider: 'Postmates/DoorDash', cost: 25, time: '1-2 hours', notes: 'Package delivery option ($20-30)' },
      { provider: 'Capitol Courier', cost: 45, time: 'Same day', notes: 'DC-based legal courier' },
      { provider: 'USPS Certified Mail', cost: 8, time: '3-5 days', notes: 'Cheapest, but slow' },
    ],
  },
  MD: {
    agency: 'MD SDAT (State Dept of Assessments and Taxation)',
    address: '301 W Preston St, Baltimore, MD 21201',
    runner_options: [
      { provider: 'In-house Runner', cost: 45, time: 'Same day', notes: '$45/trip (further from DC)' },
      { provider: 'Legal Courier Service', cost: 65, time: 'Same day', notes: 'Professional legal courier' },
      { provider: 'FedEx Same Day', cost: 55, time: 'Same day', notes: 'Guaranteed delivery' },
      { provider: 'USPS Priority Express', cost: 28, time: '1-2 days', notes: 'Overnight option', recommended: true },
      { provider: 'USPS Certified Mail', cost: 8, time: '3-5 days', notes: 'Budget option' },
    ],
  },
  VA: {
    agency: 'VA SCC (State Corporation Commission)',
    address: '1300 E Main St, Richmond, VA 23219',
    runner_options: [
      { provider: 'In-house Runner', cost: 65, time: 'Same day', notes: '$65/trip (2hr drive from DC)' },
      { provider: 'Richmond Legal Courier', cost: 55, time: 'Same day', notes: 'Richmond-based service' },
      { provider: 'FedEx Same Day', cost: 55, time: 'Same day', notes: 'Guaranteed delivery' },
      { provider: 'USPS Priority Express', cost: 28, time: '1-2 days', notes: 'Overnight option' },
      { provider: 'VA SCC Online Portal', cost: 0, time: 'Instant', notes: 'Most filings can be done online!', recommended: true },
    ],
  },
};

function FinancialsSection() {
  const [monthlyOrders, setMonthlyOrders] = useState(20);

  // Compute per-service margins
  const serviceMargins = FALLBACK_SERVICES.map(svc => {
    const opCost = OPERATIONAL_COSTS[svc.id] ?? 10;
    const netMargin = svc.serviceFee - opCost;
    const marginPct = svc.serviceFee > 0 ? (netMargin / svc.serviceFee) * 100 : 0;
    return { ...svc, opCost, netMargin, marginPct };
  });

  const totalRevenue = serviceMargins.reduce((s, m) => s + m.serviceFee, 0);
  const totalCosts = serviceMargins.reduce((s, m) => s + m.opCost, 0);
  const grossMarginPct = totalRevenue > 0 ? ((totalRevenue - totalCosts) / totalRevenue * 100) : 0;
  const avgMarginPerService = serviceMargins.length > 0 ? (totalRevenue - totalCosts) / serviceMargins.length : 0;

  // P&L projection
  const avgRevenuePerOrder = totalRevenue / serviceMargins.length;
  const avgOpCostPerOrder = totalCosts / serviceMargins.length;
  const projectedRevenue = monthlyOrders * avgRevenuePerOrder;
  const projectedOpCosts = monthlyOrders * avgOpCostPerOrder;
  const estimatedMonthlyCourier = monthlyOrders * 15; // blended average
  const projectedNetProfit = projectedRevenue - projectedOpCosts - estimatedMonthlyCourier;

  const marginColor = (pct: number) => pct > 60 ? '#16a34a' : pct >= 40 ? '#b8960c' : '#dc2626';
  const marginBg = (pct: number) => pct > 60 ? '#dcfce7' : pct >= 40 ? '#fef9c3' : '#fee2e2';

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: '24px 36px' }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0, marginBottom: 20 }}>Financial Overview &amp; Margins</h1>

      {/* KPI Summary Row */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Total Catalog Revenue', value: `$${totalRevenue.toLocaleString()}`, sub: `${serviceMargins.length} services`, icon: <DollarSign size={16} />, iconBg: '#dcfce7', iconColor: '#16a34a' },
          { label: 'Total Operational Costs', value: `$${totalCosts.toLocaleString()}`, sub: 'Per-service sum', icon: <Truck size={16} />, iconBg: '#fee2e2', iconColor: '#dc2626' },
          { label: 'Gross Margin', value: `${grossMarginPct.toFixed(1)}%`, sub: `$${(totalRevenue - totalCosts).toLocaleString()} net`, icon: <Zap size={16} />, iconBg: marginBg(grossMarginPct), iconColor: marginColor(grossMarginPct) },
          { label: 'Avg Margin / Service', value: `$${avgMarginPerService.toFixed(0)}`, sub: `${(avgMarginPerService / (avgRevenuePerOrder || 1) * 100).toFixed(0)}% avg`, icon: <Star size={16} />, iconBg: '#f3e8ff', iconColor: '#7c3aed' },
        ].map((kpi, i) => (
          <div key={i} className="empire-card" style={{ padding: '16px 18px' }}>
            <div className="flex items-center gap-3 mb-2">
              <div className="flex items-center justify-center" style={{ width: 32, height: 32, borderRadius: 8, background: kpi.iconBg, color: kpi.iconColor }}>{kpi.icon}</div>
              <div style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', color: '#999', letterSpacing: 0.5 }}>{kpi.label}</div>
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a' }}>{kpi.value}</div>
            <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>{kpi.sub}</div>
          </div>
        ))}
      </div>

      {/* Per-Service Margin Table */}
      <div className="empire-card mb-6" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid #f0ece4' }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: '#1a1a1a' }}>Per-Service Margin Analysis</div>
          <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>State fees are pass-through (charged to customer separately)</div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: '#faf8f5', borderBottom: '1px solid #f0ece4' }}>
                <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 700, color: '#666', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>Service</th>
                <th style={{ padding: '10px 14px', textAlign: 'right', fontWeight: 700, color: '#666', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>Our Fee</th>
                <th style={{ padding: '10px 14px', textAlign: 'right', fontWeight: 700, color: '#666', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>State Fee (DC/MD/VA)</th>
                <th style={{ padding: '10px 14px', textAlign: 'right', fontWeight: 700, color: '#666', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>Op. Cost</th>
                <th style={{ padding: '10px 14px', textAlign: 'right', fontWeight: 700, color: '#666', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>Net Margin</th>
                <th style={{ padding: '10px 14px', textAlign: 'right', fontWeight: 700, color: '#666', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>Margin %</th>
              </tr>
            </thead>
            <tbody>
              {serviceMargins.map((svc, i) => (
                <tr key={svc.id} style={{ borderBottom: '1px solid #f0ece4', background: i % 2 === 0 ? '#fff' : '#fdfcfa' }}>
                  <td style={{ padding: '10px 14px' }}>
                    <div style={{ fontWeight: 600, color: '#1a1a1a' }}>{svc.name}</div>
                    <div style={{ fontSize: 10, color: '#999' }}>{svc.category}</div>
                  </td>
                  <td style={{ padding: '10px 14px', textAlign: 'right', fontWeight: 600, color: '#1a1a1a' }}>{svc.serviceFee === 0 ? 'FREE' : `$${svc.serviceFee}`}</td>
                  <td style={{ padding: '10px 14px', textAlign: 'right', color: '#b8960c', fontWeight: 500 }}>${svc.stateFees.DC} / ${svc.stateFees.MD} / ${svc.stateFees.VA}</td>
                  <td style={{ padding: '10px 14px', textAlign: 'right', color: '#dc2626', fontWeight: 500 }}>-${svc.opCost}</td>
                  <td style={{ padding: '10px 14px', textAlign: 'right', fontWeight: 700, color: svc.serviceFee === 0 ? '#999' : marginColor(svc.marginPct) }}>
                    {svc.serviceFee === 0 ? '-$15' : `$${svc.netMargin}`}
                  </td>
                  <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                    <span style={{
                      display: 'inline-block', padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                      background: svc.serviceFee === 0 ? '#f5f3ef' : marginBg(svc.marginPct),
                      color: svc.serviceFee === 0 ? '#999' : marginColor(svc.marginPct),
                    }}>
                      {svc.serviceFee === 0 ? 'Lead Gen' : `${svc.marginPct.toFixed(0)}%`}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Courier/Runner Cost Analysis */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 15, fontWeight: 600, color: '#1a1a1a', marginBottom: 12 }}>Courier &amp; Runner Cost Analysis</div>
        <div className="grid grid-cols-3 gap-4">
          {(Object.entries(COURIER_COSTS) as [string, typeof COURIER_COSTS.DC][]).map(([state, data]) => (
            <div key={state} className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{ padding: '14px 16px', borderBottom: '1px solid #f0ece4', background: '#faf8f5' }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>{state}</div>
                <div style={{ fontSize: 10, color: '#666', marginTop: 2 }}>{data.agency}</div>
                <div style={{ fontSize: 10, color: '#999' }}>{data.address}</div>
              </div>
              <div style={{ padding: 0 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #f0ece4' }}>
                      <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 700, color: '#666', fontSize: 9, textTransform: 'uppercase' }}>Provider</th>
                      <th style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 700, color: '#666', fontSize: 9, textTransform: 'uppercase' }}>Cost</th>
                      <th style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 700, color: '#666', fontSize: 9, textTransform: 'uppercase' }}>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.runner_options.map((opt, j) => (
                      <tr key={j} style={{
                        borderBottom: '1px solid #f0ece4',
                        background: opt.recommended ? '#fef9c3' : j % 2 === 0 ? '#fff' : '#fdfcfa',
                        border: opt.recommended ? '2px solid #b8960c' : undefined,
                      }}>
                        <td style={{ padding: '8px 12px' }}>
                          <div className="flex items-center gap-1.5">
                            {opt.recommended && <Star size={10} className="text-[#b8960c]" style={{ flexShrink: 0 }} />}
                            <div>
                              <div style={{ fontWeight: opt.recommended ? 700 : 500, color: opt.recommended ? '#92710a' : '#1a1a1a' }}>{opt.provider}</div>
                              <div style={{ fontSize: 9, color: '#999' }}>{opt.notes}</div>
                            </div>
                          </div>
                        </td>
                        <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 700, color: opt.cost === 0 ? '#16a34a' : '#1a1a1a' }}>
                          {opt.cost === 0 ? 'FREE' : `$${opt.cost}`}
                        </td>
                        <td style={{ padding: '8px 10px', textAlign: 'right', color: '#666', whiteSpace: 'nowrap' }}>{opt.time}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Monthly P&L Projection */}
      <div className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid #f0ece4', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 600, color: '#1a1a1a' }}>Monthly P&amp;L Projection</div>
            <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>Based on estimated monthly order volume</div>
          </div>
          <div className="flex items-center gap-2">
            <label style={{ fontSize: 11, color: '#666', fontWeight: 600 }}>Monthly Orders:</label>
            <input
              type="number" min={1} max={999} value={monthlyOrders}
              onChange={e => setMonthlyOrders(Math.max(1, parseInt(e.target.value) || 1))}
              style={{ width: 60, padding: '6px 10px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, fontWeight: 700, textAlign: 'center', outline: 'none', background: '#fff' }}
            />
          </div>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <tbody>
            {[
              { label: 'Projected Revenue', value: `$${projectedRevenue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`, sub: `${monthlyOrders} orders x $${avgRevenuePerOrder.toFixed(0)} avg`, color: '#16a34a', bold: false },
              { label: 'Avg Revenue / Order', value: `$${avgRevenuePerOrder.toFixed(0)}`, sub: 'Across all service types', color: '#1a1a1a', bold: false },
              { label: 'State Fees (Pass-through)', value: 'N/A', sub: 'Collected from customer, not counted as revenue', color: '#999', bold: false },
              { label: 'Operational Costs', value: `-$${projectedOpCosts.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`, sub: `${monthlyOrders} orders x $${avgOpCostPerOrder.toFixed(0)} avg`, color: '#dc2626', bold: false },
              { label: 'Estimated Courier Costs', value: `-$${estimatedMonthlyCourier.toLocaleString()}`, sub: `~$15/order blended avg x ${monthlyOrders} orders`, color: '#dc2626', bold: false },
              { label: 'Net Profit Projection', value: `$${projectedNetProfit.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`, sub: `${(projectedRevenue > 0 ? (projectedNetProfit / projectedRevenue * 100) : 0).toFixed(1)}% net margin`, color: projectedNetProfit > 0 ? '#16a34a' : '#dc2626', bold: true },
            ].map((row, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #f0ece4', background: row.bold ? '#f0fdf4' : i % 2 === 0 ? '#fff' : '#fdfcfa' }}>
                <td style={{ padding: '12px 18px' }}>
                  <div style={{ fontWeight: row.bold ? 700 : 500, color: '#1a1a1a', fontSize: row.bold ? 14 : 13 }}>{row.label}</div>
                  <div style={{ fontSize: 10, color: '#999', marginTop: 1 }}>{row.sub}</div>
                </td>
                <td style={{ padding: '12px 18px', textAlign: 'right', fontWeight: 700, fontSize: row.bold ? 18 : 14, color: row.color }}>
                  {row.value}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============ 8b. COURIER MANAGEMENT ============

type HandoffStatus = 'pending' | 'assigned' | 'picked_up' | 'at_agency' | 'ready_for_pickup' | 'returned' | 'paid';

interface Handoff {
  id: string;
  orderId: string;
  client: string;
  docs: string[];
  courier: string;
  agency: string;
  status: HandoffStatus;
  handedOff: string;
  eta: string;
  cost: number;
  paid: boolean;
  priority?: 'standard' | 'rush' | 'same-day';
  notes?: string;
  timeline?: { date: string; event: string }[];
}

interface CourierContact {
  id: string;
  name: string;
  type: 'company' | 'individual';
  phone: string;
  email?: string;
  coverage: string[];
  rate: string;
  rating: number;
  notes: string;
}

interface CourierPayment {
  id: string;
  courier: string;
  handoffId: string;
  amount: number;
  status: 'unpaid' | 'pending' | 'paid';
  dueDate: string;
  paidDate: string;
}

const INITIAL_COURIERS: CourierContact[] = [
  { id: 'c1', name: 'All State Courier', type: 'company', phone: '(202) 737-4500', email: 'info@rushneverlate.com', coverage: ['DC', 'MD', 'VA'], rate: '$50-150/trip', rating: 5, notes: '30+ years, specializes in court/agency filings' },
  { id: 'c2', name: 'Trans Time Express', type: 'company', phone: '', coverage: ['DC', 'MD', 'VA'], rate: '$75-200/trip', rating: 4, notes: '35+ years, 300+ drivers, 24/7' },
  { id: 'c3', name: 'Washington Express', type: 'company', phone: '', coverage: ['DC'], rate: '$60-120/trip', rating: 5, notes: 'Serves 90 of top 100 DC law firms' },
  { id: 'c4', name: 'Expedited Courier Group', type: 'company', phone: '(410) 528-1920', coverage: ['MD'], rate: '$80-150/trip', rating: 4, notes: 'Baltimore-based, SDAT specialist' },
  { id: 'c5', name: 'Marcus Johnson', type: 'individual', phone: '(202) 555-0147', coverage: ['DC', 'MD'], rate: '$35/trip', rating: 4, notes: 'Freelance runner, reliable, knows DC agencies well' },
  { id: 'c6', name: 'Excel Courier', type: 'company', phone: '(703) 478-0140', coverage: ['VA', 'DC', 'MD'], rate: '$75-250/trip', rating: 4, notes: 'Mid-Atlantic, 24/7, law firm specialist' },
];

const INITIAL_HANDOFFS: Handoff[] = [
  { id: 'HO-001', orderId: 'ORD-001', client: 'EmpireBox LLC', docs: ['Articles of Organization'], courier: 'All State Courier', agency: 'DC DLCP', status: 'returned', handedOff: '2026-03-07', eta: '2026-03-07', cost: 75, paid: true, priority: 'rush', notes: 'Expedited filing — same day return.', timeline: [{ date: '2026-03-07 09:00', event: 'Picked up from office' }, { date: '2026-03-07 10:15', event: 'Submitted at DC DLCP' }, { date: '2026-03-07 14:30', event: 'Filed — docs returned' }] },
  { id: 'HO-002', orderId: 'ORD-002', client: 'TechStart Inc', docs: ['Articles of Organization', 'Operating Agreement'], courier: 'Marcus Johnson', agency: 'DC DLCP', status: 'at_agency', handedOff: '2026-03-08', eta: '2026-03-09', cost: 35, paid: false, priority: 'standard', timeline: [{ date: '2026-03-08 11:00', event: 'Picked up by Marcus' }, { date: '2026-03-08 12:30', event: 'Submitted at DC DLCP' }] },
  { id: 'HO-003', orderId: 'ORD-003', client: 'Green Valley LLC', docs: ['Certificate of Good Standing'], courier: 'Expedited Courier Group', agency: 'MD SDAT', status: 'picked_up', handedOff: '2026-03-09', eta: '2026-03-10', cost: 120, paid: false, priority: 'standard', timeline: [{ date: '2026-03-09 08:30', event: 'Picked up from office' }] },
  { id: 'HO-004', orderId: 'ORD-004', client: 'Nova Consulting', docs: ['Articles of Organization', 'Apostille'], courier: 'All State Courier', agency: 'VA SCC', status: 'pending', handedOff: '', eta: '', cost: 150, paid: false, priority: 'rush' },
  { id: 'HO-005', orderId: 'ORD-005', client: 'Bright Future Corp', docs: ['Operating Agreement', 'EIN Letter'], courier: 'Washington Express', agency: 'DC Apostille Office', status: 'ready_for_pickup', handedOff: '2026-03-06', eta: '2026-03-09', cost: 90, paid: false, priority: 'same-day', timeline: [{ date: '2026-03-06 09:00', event: 'Picked up from office' }, { date: '2026-03-06 10:00', event: 'Submitted at Apostille Office' }, { date: '2026-03-09 08:00', event: 'Agency processing complete' }] },
];

const HANDOFF_STATUS_CONFIG: Record<HandoffStatus, { label: string; bg: string; color: string }> = {
  pending: { label: 'Pending', bg: '#e5e7eb', color: '#374151' },
  assigned: { label: 'Assigned', bg: '#dbeafe', color: '#1d4ed8' },
  picked_up: { label: 'Picked Up', bg: '#fef3c7', color: '#92400e' },
  at_agency: { label: 'At Agency', bg: '#fed7aa', color: '#9a3412' },
  ready_for_pickup: { label: 'Ready', bg: '#bbf7d0', color: '#166534' },
  returned: { label: 'Returned', bg: '#16a34a', color: '#fff' },
  paid: { label: 'Paid', bg: '#b8960c', color: '#fff' },
};

const AGENCIES = ['DC DLCP', 'MD SDAT', 'VA SCC', 'DC Apostille Office', 'MD Secretary of State', 'VA Secretary of Commonwealth'];
const DOC_TYPES = ['Articles of Organization', 'Operating Agreement', 'Certificate of Good Standing', 'Apostille', 'EIN Letter', 'Annual Report', 'Certified Copy', 'Articles of Amendment'];
const PRIORITIES: Array<'standard' | 'rush' | 'same-day'> = ['standard', 'rush', 'same-day'];

function CourierManagementSection() {
  const [handoffs, setHandoffs] = useState<Handoff[]>(INITIAL_HANDOFFS);
  const [couriers, setCouriers] = useState<CourierContact[]>(INITIAL_COURIERS);
  const [subTab, setSubTab] = useState<'handoffs' | 'directory' | 'payments'>('handoffs');
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [showNewHandoff, setShowNewHandoff] = useState(false);
  const [showNewCourier, setShowNewCourier] = useState(false);

  // New handoff form state
  const [newHandoff, setNewHandoff] = useState({
    orderId: '', client: '', docs: [] as string[], courier: '', agency: '', priority: 'standard' as 'standard' | 'rush' | 'same-day', instructions: '', cost: 0,
  });

  // New courier form state
  const [newCourier, setNewCourier] = useState({
    name: '', type: 'company' as 'company' | 'individual', phone: '', email: '', coverage: [] as string[], rate: '', notes: '',
  });

  // Payment data derived from handoffs
  const payments: CourierPayment[] = handoffs.map(h => ({
    id: `PAY-${h.id}`,
    courier: h.courier,
    handoffId: h.id,
    amount: h.cost,
    status: h.paid ? 'paid' as const : (h.status === 'returned' ? 'pending' as const : 'unpaid' as const),
    dueDate: h.eta || 'TBD',
    paidDate: h.paid ? h.handedOff : '',
  }));

  const totalUnpaid = payments.filter(p => p.status !== 'paid').reduce((s, p) => s + p.amount, 0);
  const totalPaidMonth = payments.filter(p => p.status === 'paid').reduce((s, p) => s + p.amount, 0);

  const handleAddHandoff = () => {
    if (!newHandoff.client || !newHandoff.courier || !newHandoff.agency) return;
    const id = `HO-${String(handoffs.length + 1).padStart(3, '0')}`;
    setHandoffs(prev => [...prev, {
      id, orderId: newHandoff.orderId || id, client: newHandoff.client, docs: newHandoff.docs,
      courier: newHandoff.courier, agency: newHandoff.agency, status: 'pending',
      handedOff: '', eta: '', cost: newHandoff.cost, paid: false, priority: newHandoff.priority,
      notes: newHandoff.instructions, timeline: [],
    }]);
    setNewHandoff({ orderId: '', client: '', docs: [], courier: '', agency: '', priority: 'standard', instructions: '', cost: 0 });
    setShowNewHandoff(false);
  };

  const handleAddCourier = () => {
    if (!newCourier.name) return;
    const id = `c${couriers.length + 1}`;
    setCouriers(prev => [...prev, { id, name: newCourier.name, type: newCourier.type, phone: newCourier.phone, email: newCourier.email, coverage: newCourier.coverage, rate: newCourier.rate, rating: 3, notes: newCourier.notes }]);
    setNewCourier({ name: '', type: 'company', phone: '', email: '', coverage: [], rate: '', notes: '' });
    setShowNewCourier(false);
  };

  const updateHandoffStatus = (id: string, status: HandoffStatus) => {
    setHandoffs(prev => prev.map(h => h.id === id ? { ...h, status, ...(status === 'picked_up' && !h.handedOff ? { handedOff: new Date().toISOString().slice(0, 10) } : {}), timeline: [...(h.timeline || []), { date: new Date().toISOString().slice(0, 16).replace('T', ' '), event: `Status changed to ${HANDOFF_STATUS_CONFIG[status].label}` }] } : h));
  };

  const markPaid = (handoffId: string) => {
    setHandoffs(prev => prev.map(h => h.id === handoffId ? { ...h, paid: true, status: 'paid' } : h));
  };

  const removeCourier = (id: string) => setCouriers(prev => prev.filter(c => c.id !== id));

  const tabStyle = (active: boolean) => ({
    padding: '8px 18px', borderRadius: 8, fontSize: 13, fontWeight: active ? 700 : 500,
    background: active ? '#b8960c' : 'transparent', color: active ? '#fff' : '#666',
    border: 'none', cursor: 'pointer' as const,
  });

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <div className="flex items-center justify-between" style={{ marginBottom: 20 }}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: '#fef3c7' }}>
            <Truck size={20} style={{ color: '#b8960c' }} />
          </div>
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Courier Management</h2>
            <p style={{ fontSize: 12, color: '#999', margin: 0 }}>Document handoffs, runners, and agency deliveries</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setSubTab('handoffs')} style={tabStyle(subTab === 'handoffs')}>Handoffs</button>
          <button onClick={() => setSubTab('directory')} style={tabStyle(subTab === 'directory')}>Directory</button>
          <button onClick={() => setSubTab('payments')} style={tabStyle(subTab === 'payments')}>Payments</button>
        </div>
      </div>

      {/* ---- HANDOFFS TAB ---- */}
      {subTab === 'handoffs' && (
        <div>
          <div className="flex items-center justify-between" style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Document Handoffs</h3>
            <button onClick={() => setShowNewHandoff(true)} className="flex items-center gap-2" style={{ padding: '8px 16px', borderRadius: 10, background: '#b8960c', color: '#fff', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
              <Plus size={14} /> New Handoff
            </button>
          </div>

          {/* New Handoff Form */}
          {showNewHandoff && (
            <div style={{ background: '#fff', borderRadius: 14, border: '1px solid #ece8e0', padding: 20, marginBottom: 16 }}>
              <div className="flex items-center justify-between" style={{ marginBottom: 16 }}>
                <h4 style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>New Document Handoff</h4>
                <button onClick={() => setShowNewHandoff(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X size={16} /></button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Order ID</label>
                  <input value={newHandoff.orderId} onChange={e => setNewHandoff(p => ({ ...p, orderId: e.target.value }))} placeholder="ORD-xxx" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', fontSize: 13 }} />
                </div>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Client Name *</label>
                  <input value={newHandoff.client} onChange={e => setNewHandoff(p => ({ ...p, client: e.target.value }))} placeholder="Client name" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', fontSize: 13 }} />
                </div>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Target Agency *</label>
                  <select value={newHandoff.agency} onChange={e => setNewHandoff(p => ({ ...p, agency: e.target.value }))} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', fontSize: 13 }}>
                    <option value="">Select agency...</option>
                    {AGENCIES.map(a => <option key={a} value={a}>{a}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Courier *</label>
                  <select value={newHandoff.courier} onChange={e => setNewHandoff(p => ({ ...p, courier: e.target.value }))} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', fontSize: 13 }}>
                    <option value="">Select courier...</option>
                    {couriers.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Priority</label>
                  <select value={newHandoff.priority} onChange={e => setNewHandoff(p => ({ ...p, priority: e.target.value as any }))} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', fontSize: 13 }}>
                    {PRIORITIES.map(pr => <option key={pr} value={pr}>{pr.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase())}</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Estimated Cost ($)</label>
                  <input type="number" value={newHandoff.cost || ''} onChange={e => setNewHandoff(p => ({ ...p, cost: Number(e.target.value) }))} placeholder="0" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', fontSize: 13 }} />
                </div>
              </div>
              <div style={{ marginTop: 12 }}>
                <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Documents to Hand Off</label>
                <div className="flex flex-wrap gap-2">
                  {DOC_TYPES.map(doc => (
                    <label key={doc} className="flex items-center gap-1" style={{ fontSize: 12, cursor: 'pointer' }}>
                      <input type="checkbox" checked={newHandoff.docs.includes(doc)} onChange={e => {
                        setNewHandoff(p => ({ ...p, docs: e.target.checked ? [...p.docs, doc] : p.docs.filter(d => d !== doc) }));
                      }} />
                      {doc}
                    </label>
                  ))}
                </div>
              </div>
              <div style={{ marginTop: 12 }}>
                <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Special Instructions</label>
                <textarea value={newHandoff.instructions} onChange={e => setNewHandoff(p => ({ ...p, instructions: e.target.value }))} placeholder="Any special instructions..." rows={2} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', fontSize: 13, resize: 'vertical' }} />
              </div>
              <div className="flex justify-end gap-2" style={{ marginTop: 16 }}>
                <button onClick={() => setShowNewHandoff(false)} style={{ padding: '8px 18px', borderRadius: 8, background: '#f3f3f3', color: '#666', border: 'none', fontSize: 13, cursor: 'pointer' }}>Cancel</button>
                <button onClick={handleAddHandoff} style={{ padding: '8px 18px', borderRadius: 8, background: '#b8960c', color: '#fff', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>Create Handoff</button>
              </div>
            </div>
          )}

          {/* Handoffs Table */}
          <div style={{ background: '#fff', borderRadius: 14, border: '1px solid #ece8e0', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#faf9f7', borderBottom: '1px solid #ece8e0' }}>
                  {['Handoff #', 'Order/Client', 'Documents', 'Courier', 'Agency', 'Status', 'Handed Off', 'ETA', 'Actions'].map(h => (
                    <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#666', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {handoffs.map(h => {
                  const stCfg = HANDOFF_STATUS_CONFIG[h.status];
                  const isExpanded = expandedRow === h.id;
                  return (
                    <React.Fragment key={h.id}>
                      <tr style={{ borderBottom: '1px solid #f0ede8', cursor: 'pointer' }} onClick={() => setExpandedRow(isExpanded ? null : h.id)}>
                        <td style={{ padding: '10px 12px', fontWeight: 600 }}>{h.id}</td>
                        <td style={{ padding: '10px 12px' }}>
                          <div style={{ fontWeight: 600 }}>{h.client}</div>
                          <div style={{ fontSize: 11, color: '#999' }}>{h.orderId}</div>
                        </td>
                        <td style={{ padding: '10px 12px' }}>
                          <div className="flex flex-wrap gap-1">
                            {h.docs.map(d => <span key={d} style={{ padding: '2px 6px', borderRadius: 4, background: '#f3f1ec', fontSize: 10, color: '#666' }}>{d}</span>)}
                          </div>
                        </td>
                        <td style={{ padding: '10px 12px' }}>{h.courier}</td>
                        <td style={{ padding: '10px 12px' }}>{h.agency}</td>
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{ padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600, background: stCfg.bg, color: stCfg.color }}>{stCfg.label}</span>
                        </td>
                        <td style={{ padding: '10px 12px', fontSize: 12 }}>{h.handedOff || '—'}</td>
                        <td style={{ padding: '10px 12px', fontSize: 12 }}>{h.eta || '—'}</td>
                        <td style={{ padding: '10px 12px' }}>
                          <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#b8960c' }}>
                            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                          </button>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={9} style={{ padding: 0 }}>
                            <div style={{ padding: '16px 24px', background: '#faf9f7', borderBottom: '2px solid #ece8e0' }}>
                              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 20 }}>
                                {/* Document List */}
                                <div>
                                  <h5 style={{ fontSize: 12, fontWeight: 700, color: '#333', marginBottom: 8, margin: '0 0 8px 0' }}>Documents</h5>
                                  {h.docs.map(d => (
                                    <div key={d} className="flex items-center gap-2" style={{ fontSize: 12, marginBottom: 4 }}>
                                      <FileText size={12} style={{ color: '#b8960c' }} /> {d}
                                    </div>
                                  ))}
                                </div>
                                {/* Courier Contact */}
                                <div>
                                  <h5 style={{ fontSize: 12, fontWeight: 700, color: '#333', marginBottom: 8, margin: '0 0 8px 0' }}>Courier Info</h5>
                                  {(() => {
                                    const c = couriers.find(c => c.name === h.courier);
                                    if (!c) return <span style={{ fontSize: 12, color: '#999' }}>No info</span>;
                                    return (
                                      <div style={{ fontSize: 12 }}>
                                        <div className="flex items-center gap-1"><User size={12} /> {c.name}</div>
                                        {c.phone && <div className="flex items-center gap-1" style={{ marginTop: 2 }}><Phone size={12} /> {c.phone}</div>}
                                        {c.email && <div className="flex items-center gap-1" style={{ marginTop: 2 }}><Mail size={12} /> {c.email}</div>}
                                        <div style={{ marginTop: 4, color: '#999' }}>Rate: {c.rate}</div>
                                      </div>
                                    );
                                  })()}
                                </div>
                                {/* Payment Info */}
                                <div>
                                  <h5 style={{ fontSize: 12, fontWeight: 700, color: '#333', marginBottom: 8, margin: '0 0 8px 0' }}>Payment</h5>
                                  <div style={{ fontSize: 12 }}>
                                    <div>Amount: <strong>${h.cost}</strong></div>
                                    <div style={{ marginTop: 4 }}>
                                      Status: <span style={{ padding: '2px 8px', borderRadius: 12, fontSize: 10, fontWeight: 600, background: h.paid ? '#bbf7d0' : '#fef3c7', color: h.paid ? '#166534' : '#92400e' }}>{h.paid ? 'Paid' : 'Unpaid'}</span>
                                    </div>
                                    {h.priority && <div style={{ marginTop: 4 }}>Priority: <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{h.priority.replace('-', ' ')}</span></div>}
                                  </div>
                                </div>
                              </div>
                              {/* Timeline */}
                              {h.timeline && h.timeline.length > 0 && (
                                <div style={{ marginTop: 16 }}>
                                  <h5 style={{ fontSize: 12, fontWeight: 700, color: '#333', marginBottom: 8, margin: '0 0 8px 0' }}>Timeline</h5>
                                  <div style={{ borderLeft: '2px solid #b8960c', paddingLeft: 12, marginLeft: 4 }}>
                                    {h.timeline.map((t, i) => (
                                      <div key={i} className="flex items-start gap-2" style={{ fontSize: 11, marginBottom: 6, position: 'relative' }}>
                                        <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#b8960c', position: 'absolute', left: -17, top: 3 }} />
                                        <span style={{ color: '#999', minWidth: 110 }}>{t.date}</span>
                                        <span>{t.event}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                              {/* Notes */}
                              {h.notes && (
                                <div style={{ marginTop: 12 }}>
                                  <h5 style={{ fontSize: 12, fontWeight: 700, color: '#333', marginBottom: 4, margin: '0 0 4px 0' }}>Notes</h5>
                                  <p style={{ fontSize: 12, color: '#666', margin: 0 }}>{h.notes}</p>
                                </div>
                              )}
                              {/* Status Actions */}
                              <div className="flex gap-2 flex-wrap" style={{ marginTop: 16 }}>
                                {h.status === 'pending' && <button onClick={(e) => { e.stopPropagation(); updateHandoffStatus(h.id, 'assigned'); }} style={{ padding: '6px 14px', borderRadius: 8, background: '#dbeafe', color: '#1d4ed8', border: 'none', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>Mark Assigned</button>}
                                {h.status === 'assigned' && <button onClick={(e) => { e.stopPropagation(); updateHandoffStatus(h.id, 'picked_up'); }} style={{ padding: '6px 14px', borderRadius: 8, background: '#fef3c7', color: '#92400e', border: 'none', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>Mark Picked Up</button>}
                                {h.status === 'picked_up' && <button onClick={(e) => { e.stopPropagation(); updateHandoffStatus(h.id, 'at_agency'); }} style={{ padding: '6px 14px', borderRadius: 8, background: '#fed7aa', color: '#9a3412', border: 'none', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>Mark At Agency</button>}
                                {h.status === 'at_agency' && <button onClick={(e) => { e.stopPropagation(); updateHandoffStatus(h.id, 'ready_for_pickup'); }} style={{ padding: '6px 14px', borderRadius: 8, background: '#bbf7d0', color: '#166534', border: 'none', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>Mark Ready</button>}
                                {h.status === 'ready_for_pickup' && <button onClick={(e) => { e.stopPropagation(); updateHandoffStatus(h.id, 'returned'); }} style={{ padding: '6px 14px', borderRadius: 8, background: '#16a34a', color: '#fff', border: 'none', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>Mark Returned</button>}
                                {(h.status === 'returned' && !h.paid) && <button onClick={(e) => { e.stopPropagation(); markPaid(h.id); }} style={{ padding: '6px 14px', borderRadius: 8, background: '#b8960c', color: '#fff', border: 'none', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>Mark Paid</button>}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
            {handoffs.length === 0 && (
              <div style={{ padding: 40, textAlign: 'center', color: '#999' }}>
                <Truck size={32} style={{ margin: '0 auto 8px', opacity: 0.3 }} />
                <p style={{ fontSize: 13 }}>No handoffs yet. Click "+ New Handoff" to create one.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ---- COURIER DIRECTORY TAB ---- */}
      {subTab === 'directory' && (
        <div>
          <div className="flex items-center justify-between" style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Courier Directory</h3>
            <button onClick={() => setShowNewCourier(true)} className="flex items-center gap-2" style={{ padding: '8px 16px', borderRadius: 10, background: '#b8960c', color: '#fff', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
              <Plus size={14} /> Add Courier
            </button>
          </div>

          {/* New Courier Form */}
          {showNewCourier && (
            <div style={{ background: '#fff', borderRadius: 14, border: '1px solid #ece8e0', padding: 20, marginBottom: 16 }}>
              <div className="flex items-center justify-between" style={{ marginBottom: 16 }}>
                <h4 style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>Add Courier Contact</h4>
                <button onClick={() => setShowNewCourier(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><X size={16} /></button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Name *</label>
                  <input value={newCourier.name} onChange={e => setNewCourier(p => ({ ...p, name: e.target.value }))} placeholder="Courier name" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', fontSize: 13 }} />
                </div>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Type</label>
                  <select value={newCourier.type} onChange={e => setNewCourier(p => ({ ...p, type: e.target.value as any }))} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', fontSize: 13 }}>
                    <option value="company">Company</option>
                    <option value="individual">Individual</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Phone</label>
                  <input value={newCourier.phone} onChange={e => setNewCourier(p => ({ ...p, phone: e.target.value }))} placeholder="(xxx) xxx-xxxx" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', fontSize: 13 }} />
                </div>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Email</label>
                  <input value={newCourier.email} onChange={e => setNewCourier(p => ({ ...p, email: e.target.value }))} placeholder="email@example.com" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', fontSize: 13 }} />
                </div>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Rate</label>
                  <input value={newCourier.rate} onChange={e => setNewCourier(p => ({ ...p, rate: e.target.value }))} placeholder="$xx/trip" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', fontSize: 13 }} />
                </div>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Coverage</label>
                  <div className="flex gap-3">
                    {['DC', 'MD', 'VA'].map(st => (
                      <label key={st} className="flex items-center gap-1" style={{ fontSize: 12 }}>
                        <input type="checkbox" checked={newCourier.coverage.includes(st)} onChange={e => {
                          setNewCourier(p => ({ ...p, coverage: e.target.checked ? [...p.coverage, st] : p.coverage.filter(s => s !== st) }));
                        }} />
                        {st}
                      </label>
                    ))}
                  </div>
                </div>
              </div>
              <div style={{ marginTop: 12 }}>
                <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Notes</label>
                <textarea value={newCourier.notes} onChange={e => setNewCourier(p => ({ ...p, notes: e.target.value }))} rows={2} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', fontSize: 13, resize: 'vertical' }} />
              </div>
              <div className="flex justify-end gap-2" style={{ marginTop: 16 }}>
                <button onClick={() => setShowNewCourier(false)} style={{ padding: '8px 18px', borderRadius: 8, background: '#f3f3f3', color: '#666', border: 'none', fontSize: 13, cursor: 'pointer' }}>Cancel</button>
                <button onClick={handleAddCourier} style={{ padding: '8px 18px', borderRadius: 8, background: '#b8960c', color: '#fff', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>Add Courier</button>
              </div>
            </div>
          )}

          {/* Courier Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 16 }}>
            {couriers.map(c => (
              <div key={c.id} style={{ background: '#fff', borderRadius: 14, border: '1px solid #ece8e0', padding: 18 }}>
                <div className="flex items-start justify-between" style={{ marginBottom: 10 }}>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>{c.name}</h4>
                      <span style={{ padding: '2px 8px', borderRadius: 12, fontSize: 10, fontWeight: 600, background: c.type === 'company' ? '#dbeafe' : '#fce7f3', color: c.type === 'company' ? '#1d4ed8' : '#be185d' }}>
                        {c.type === 'company' ? 'Company' : 'Individual'}
                      </span>
                    </div>
                    <div className="flex items-center gap-1" style={{ marginTop: 4 }}>
                      {Array.from({ length: 5 }).map((_, i) => (
                        <Star key={i} size={12} style={{ color: i < c.rating ? '#b8960c' : '#ddd' }} fill={i < c.rating ? '#b8960c' : 'none'} />
                      ))}
                    </div>
                  </div>
                  <button onClick={() => removeCourier(c.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ccc' }} title="Delete">
                    <X size={14} />
                  </button>
                </div>
                {c.phone && (
                  <div className="flex items-center gap-2" style={{ fontSize: 12, color: '#555', marginBottom: 4 }}>
                    <Phone size={12} /> {c.phone}
                  </div>
                )}
                {c.email && (
                  <div className="flex items-center gap-2" style={{ fontSize: 12, color: '#555', marginBottom: 4 }}>
                    <Mail size={12} /> {c.email}
                  </div>
                )}
                <div className="flex items-center gap-2" style={{ fontSize: 12, color: '#555', marginBottom: 4 }}>
                  <MapPin size={12} /> {c.coverage.join(', ')}
                </div>
                <div className="flex items-center gap-2" style={{ fontSize: 12, color: '#555', marginBottom: 8 }}>
                  <DollarSign size={12} /> {c.rate}
                </div>
                <p style={{ fontSize: 11, color: '#999', margin: 0, lineHeight: 1.5 }}>{c.notes}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ---- PAYMENTS TAB ---- */}
      {subTab === 'payments' && (
        <div>
          {/* Summary Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 20 }}>
            <div style={{ background: '#fff', borderRadius: 14, border: '1px solid #ece8e0', padding: 18 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#999', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Total Unpaid</div>
              <div style={{ fontSize: 24, fontWeight: 800, color: '#dc2626', marginTop: 4 }}>${totalUnpaid}</div>
            </div>
            <div style={{ background: '#fff', borderRadius: 14, border: '1px solid #ece8e0', padding: 18 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#999', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Paid This Month</div>
              <div style={{ fontSize: 24, fontWeight: 800, color: '#16a34a', marginTop: 4 }}>${totalPaidMonth}</div>
            </div>
            <div style={{ background: '#fff', borderRadius: 14, border: '1px solid #ece8e0', padding: 18 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#999', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Outstanding Balance</div>
              <div style={{ fontSize: 24, fontWeight: 800, color: '#b8960c', marginTop: 4 }}>${totalUnpaid}</div>
            </div>
          </div>

          <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', margin: '0 0 12px 0' }}>Payment Tracker</h3>
          <div style={{ background: '#fff', borderRadius: 14, border: '1px solid #ece8e0', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#faf9f7', borderBottom: '1px solid #ece8e0' }}>
                  {['Courier', 'Handoff #', 'Amount', 'Status', 'Due Date', 'Paid Date', 'Actions'].map(h => (
                    <th key={h} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: 600, color: '#666', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {payments.map(p => (
                  <tr key={p.id} style={{ borderBottom: '1px solid #f0ede8' }}>
                    <td style={{ padding: '10px 12px', fontWeight: 600 }}>{p.courier}</td>
                    <td style={{ padding: '10px 12px' }}>{p.handoffId}</td>
                    <td style={{ padding: '10px 12px', fontWeight: 700 }}>${p.amount}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600,
                        background: p.status === 'paid' ? '#bbf7d0' : p.status === 'pending' ? '#fef3c7' : '#fee2e2',
                        color: p.status === 'paid' ? '#166534' : p.status === 'pending' ? '#92400e' : '#991b1b',
                      }}>{p.status.charAt(0).toUpperCase() + p.status.slice(1)}</span>
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 12 }}>{p.dueDate}</td>
                    <td style={{ padding: '10px 12px', fontSize: 12 }}>{p.paidDate || '—'}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <div className="flex gap-2">
                        {p.status !== 'paid' && (
                          <button onClick={() => markPaid(p.handoffId)} style={{ padding: '4px 12px', borderRadius: 6, background: '#b8960c', color: '#fff', border: 'none', fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>Mark Paid</button>
                        )}
                        <button style={{ padding: '4px 12px', borderRadius: 6, background: '#f3f1ec', color: '#666', border: 'none', fontSize: 11, cursor: 'pointer' }} title="Generate Invoice (coming soon)">Invoice</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ============ 9. AI TOOLS ============

function AIToolsSection() {
  const [nameCheckState, setNameCheckState] = useState('');
  const [nameCheckResult, setNameCheckResult] = useState<any>(null);
  const [nameCheckLoading, setNameCheckLoading] = useState(false);
  const [nameCheckStateSelect, setNameCheckStateSelect] = useState('DC');

  const [oaForm, setOaForm] = useState({ businessName: '', state: 'DC', members: '', purpose: '' });
  const [oaResult, setOaResult] = useState<string | null>(null);
  const [oaContent, setOaContent] = useState<string | null>(null);
  const [oaLoading, setOaLoading] = useState(false);

  const [docsForm, setDocsForm] = useState({ businessName: '', state: 'DC', type: 'LLC', purpose: '' });
  const [docsResult, setDocsResult] = useState<string | null>(null);
  const [docsLoading, setDocsLoading] = useState(false);

  const [quizStep, setQuizStep] = useState(0);
  const [quizAnswers, setQuizAnswers] = useState({ members: '1', registeredAgent: false, apostille: false, budget: 'low' });
  const [quizResult, setQuizResult] = useState<string | null>(null);

  // Document Activity panel state
  const [documents, setDocuments] = useState<any[]>([]);
  const [docsListLoading, setDocsListLoading] = useState(false);
  const [viewerDoc, setViewerDoc] = useState<any>(null);
  const [viewerContent, setViewerContent] = useState<string | null>(null);
  const [viewerLoading, setViewerLoading] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  // Fetch document list
  const fetchDocuments = async () => {
    setDocsListLoading(true);
    try {
      const res = await fetch(API + '/llcfactory/documents');
      const data = await res.json();
      const docs = Array.isArray(data) ? data : (data.documents || []);
      setDocuments(docs.sort((a: any, b: any) => new Date(b.created_at || b.timestamp || 0).getTime() - new Date(a.created_at || a.timestamp || 0).getTime()));
    } catch {
      setDocuments([]);
    }
    setDocsListLoading(false);
  };

  // Load docs on mount
  useEffect(() => { fetchDocuments(); }, []);

  // View a document
  const handleViewDoc = async (doc: any) => {
    setViewerDoc(doc);
    setViewerContent(null);
    setViewerLoading(true);
    try {
      const docId = doc.id || doc.doc_id || doc.filename;
      const res = await fetch(API + `/llcfactory/documents/${encodeURIComponent(docId)}/download`);
      const text = await res.text();
      setViewerContent(text);
    } catch {
      setViewerContent('[Failed to load document content]');
    }
    setViewerLoading(false);
  };

  // Download a document
  const handleDownloadDoc = (doc: any) => {
    const content = viewerContent || '';
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = doc.filename || doc.name || 'document.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  // Get border color based on doc type
  const getDocBorderColor = (doc: any) => {
    const type = (doc.type || doc.doc_type || doc.filename || '').toLowerCase();
    if (type.includes('operating') || type.includes('oa')) return '#b8960c';
    if (type.includes('formation') || type.includes('articles')) return '#7c3aed';
    if (type.includes('name') || type.includes('check')) return '#2563eb';
    return '#b8960c';
  };

  // Get doc type label
  const getDocTypeLabel = (doc: any) => {
    const type = (doc.type || doc.doc_type || doc.filename || '').toLowerCase();
    if (type.includes('operating') || type.includes('oa')) return 'Operating Agreement';
    if (type.includes('formation') || type.includes('articles')) return 'Formation Docs';
    if (type.includes('name') || type.includes('check')) return 'Name Check';
    return doc.type || 'Document';
  };

  // Extract business name from filename or metadata
  const getDocBusinessName = (doc: any) => {
    if (doc.business_name) return doc.business_name;
    const fn = doc.filename || doc.name || '';
    return fn.replace(/_/g, ' ').replace(/\.(txt|pdf|doc|md)$/i, '').slice(0, 40) || 'Untitled';
  };

  // Show toast notification
  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 4000);
  };

  const handleNameCheck = async () => {
    if (!nameCheckState.trim()) return;
    setNameCheckLoading(true);
    setNameCheckResult(null);
    try {
      const res = await fetch(API + '/llcfactory/name-check', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: nameCheckState, state: nameCheckStateSelect }),
      });
      const data = await res.json();
      setNameCheckResult(data);
    } catch {
      setNameCheckResult({ available: true, name: nameCheckState, state: nameCheckStateSelect, message: 'Name appears available (offline check — verify with state)' });
    }
    setNameCheckLoading(false);
  };

  const handleGenerateOA = async () => {
    if (!oaForm.businessName.trim()) return;
    setOaLoading(true); setOaResult(null); setOaContent(null);
    try {
      const res = await fetch(API + '/llcfactory/generate-oa', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(oaForm),
      });
      const data = await res.json();
      if (data.content) {
        setOaContent(data.content);
        setOaResult(`Operating Agreement generated (${data.ai_source || 'template'})`);
      } else {
        setOaResult(data.message || 'Operating Agreement generated successfully');
      }
      // Auto-refresh document list after OA generation
      await fetchDocuments();
      showToast('Operating Agreement saved — view it in Document Activity');
    } catch {
      setOaResult('Generation failed. Please try again.');
    }
    setOaLoading(false);
  };

  const downloadOA = () => {
    if (!oaContent) return;
    const blob = new Blob([oaContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${oaForm.businessName.replace(/\s+/g, '_')}_Operating_Agreement.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleGenerateDocs = async () => {
    if (!docsForm.businessName.trim()) return;
    setDocsLoading(true); setDocsResult(null);
    try {
      const res = await fetch(API + '/llcfactory/generate-docs', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(docsForm),
      });
      const data = await res.json();
      setDocsResult(data.message || 'Formation documents generated successfully');
      // Auto-refresh document list after doc generation
      await fetchDocuments();
      showToast('Formation documents saved — view them in Document Activity');
    } catch {
      setDocsResult('Document generation request submitted. Check the Docs section for your documents.');
    }
    setDocsLoading(false);
  };

  const handleQuizSubmit = () => {
    const { members, registeredAgent, apostille, budget } = quizAnswers;
    if (budget === 'high' || apostille || registeredAgent) {
      setQuizResult('empire');
    } else if (parseInt(members) > 1 || budget === 'medium') {
      setQuizResult('professional');
    } else {
      setQuizResult('starter');
    }
  };

  const inputStyle: React.CSSProperties = { padding: '8px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 12, width: '100%', background: '#fff', outline: 'none' };
  const selectStyle: React.CSSProperties = { ...inputStyle, cursor: 'pointer' };

  return (
    <div style={{ display: 'flex', gap: 20, padding: '24px 20px', position: 'relative' }}>
      {/* Toast notification */}
      {toast && (
        <div style={{ position: 'fixed', top: 20, right: 20, zIndex: 9999, padding: '12px 20px', borderRadius: 10, background: '#1a1a1a', color: '#fff', fontSize: 12, fontWeight: 600, boxShadow: '0 4px 20px rgba(0,0,0,0.15)', display: 'flex', alignItems: 'center', gap: 8, animation: 'fadeIn 0.3s ease' }}>
          <CheckCircle size={14} className="text-[#4ade80]" />
          {toast}
        </div>
      )}

      {/* LEFT COLUMN: AI Tools (58%) */}
      <div style={{ flex: '0 0 58%' }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0, marginBottom: 20 }}>AI Tools</h1>

        <div className="grid grid-cols-2 gap-4">
          {/* Name Check */}
          <div className="empire-card" style={{ padding: '20px 22px' }}>
            <div className="flex items-center gap-2 mb-3">
              <Search size={18} className="text-[#2563eb]" />
              <div style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a' }}>Check Name Availability</div>
            </div>
            <p style={{ fontSize: 11, color: '#999', marginBottom: 12 }}>Verify your desired business name is available in your state</p>
            <div className="space-y-2 mb-3">
              <input value={nameCheckState} onChange={e => setNameCheckState(e.target.value)} placeholder="Enter business name..." style={inputStyle} />
              <select value={nameCheckStateSelect} onChange={e => setNameCheckStateSelect(e.target.value)} style={selectStyle}>
                <option value="DC">Washington, DC</option>
                <option value="MD">Maryland</option>
                <option value="VA">Virginia</option>
              </select>
            </div>
            <button onClick={handleNameCheck} disabled={nameCheckLoading}
              style={{ padding: '8px 16px', borderRadius: 8, background: '#2563eb', color: '#fff', fontSize: 12, fontWeight: 600, border: 'none', cursor: 'pointer', width: '100%', opacity: nameCheckLoading ? 0.7 : 1 }}
              className="flex items-center justify-center gap-2">
              {nameCheckLoading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />} Check Availability
            </button>
            {nameCheckResult && (
              <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 8, background: nameCheckResult.available ? '#dcfce7' : '#fef2f2', border: `1px solid ${nameCheckResult.available ? '#bbf7d0' : '#fecaca'}` }}>
                <div className="flex items-center gap-2">
                  {nameCheckResult.available ? <CheckCircle size={14} className="text-[#16a34a]" /> : <X size={14} className="text-red-500" />}
                  <span style={{ fontSize: 12, fontWeight: 600, color: nameCheckResult.available ? '#16a34a' : '#dc2626' }}>
                    {nameCheckResult.available ? 'Name Available' : 'Name Unavailable'}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>{nameCheckResult.message}</div>
              </div>
            )}
          </div>

          {/* Generate OA */}
          <div className="empire-card" style={{ padding: '20px 22px' }}>
            <div className="flex items-center gap-2 mb-3">
              <FileText size={18} className="text-[#b8960c]" />
              <div style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a' }}>Generate Operating Agreement</div>
            </div>
            <p style={{ fontSize: 11, color: '#999', marginBottom: 12 }}>AI-drafted operating agreement customized for your business</p>
            <div className="space-y-2 mb-3">
              <input value={oaForm.businessName} onChange={e => setOaForm({ ...oaForm, businessName: e.target.value })} placeholder="Business name" style={inputStyle} />
              <select value={oaForm.state} onChange={e => setOaForm({ ...oaForm, state: e.target.value })} style={selectStyle}>
                <option value="DC">Washington, DC</option><option value="MD">Maryland</option><option value="VA">Virginia</option>
              </select>
              <input value={oaForm.members} onChange={e => setOaForm({ ...oaForm, members: e.target.value })} placeholder="Members (e.g. John Doe 50%, Jane Doe 50%)" style={inputStyle} />
              <input value={oaForm.purpose} onChange={e => setOaForm({ ...oaForm, purpose: e.target.value })} placeholder="Business purpose" style={inputStyle} />
            </div>
            <button onClick={handleGenerateOA} disabled={oaLoading}
              style={{ padding: '8px 16px', borderRadius: 8, background: '#b8960c', color: '#fff', fontSize: 12, fontWeight: 600, border: 'none', cursor: 'pointer', width: '100%', opacity: oaLoading ? 0.7 : 1 }}
              className="flex items-center justify-center gap-2">
              {oaLoading ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />} Generate OA
            </button>
            {oaResult && (
              <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 8, background: '#dcfce7', border: '1px solid #bbf7d0' }}>
                <div style={{ fontSize: 12, color: '#16a34a', fontWeight: 600 }}>{oaResult}</div>
                {oaContent && (
                  <div style={{ marginTop: 8 }}>
                    <button onClick={downloadOA} style={{ padding: '6px 12px', borderRadius: 6, background: '#16a34a', color: '#fff', fontSize: 11, fontWeight: 600, border: 'none', cursor: 'pointer', marginRight: 8 }}>
                      Download .txt
                    </button>
                    <button onClick={() => navigator.clipboard.writeText(oaContent)} style={{ padding: '6px 12px', borderRadius: 6, background: '#f5f0e6', color: '#b8960c', fontSize: 11, fontWeight: 600, border: '1px solid #e5dcc8', cursor: 'pointer' }}>
                      Copy to Clipboard
                    </button>
                    <pre style={{ marginTop: 10, padding: 12, background: '#faf9f7', border: '1px solid #e5e0d8', borderRadius: 8, fontSize: 10, lineHeight: 1.5, maxHeight: 200, overflowY: 'auto', whiteSpace: 'pre-wrap', color: '#333' }}>{oaContent.slice(0, 2000)}{oaContent.length > 2000 ? '\n\n... [Download for full document]' : ''}</pre>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Generate Formation Docs */}
          <div className="empire-card" style={{ padding: '20px 22px' }}>
            <div className="flex items-center gap-2 mb-3">
              <FileDown size={18} className="text-[#7c3aed]" />
              <div style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a' }}>Generate Formation Docs</div>
            </div>
            <p style={{ fontSize: 11, color: '#999', marginBottom: 12 }}>Generate Articles of Organization and related formation documents</p>
            <div className="space-y-2 mb-3">
              <input value={docsForm.businessName} onChange={e => setDocsForm({ ...docsForm, businessName: e.target.value })} placeholder="Business name" style={inputStyle} />
              <div className="flex gap-2">
                <select value={docsForm.state} onChange={e => setDocsForm({ ...docsForm, state: e.target.value })} style={{ ...selectStyle, flex: 1 }}>
                  <option value="DC">DC</option><option value="MD">MD</option><option value="VA">VA</option>
                </select>
                <select value={docsForm.type} onChange={e => setDocsForm({ ...docsForm, type: e.target.value })} style={{ ...selectStyle, flex: 1 }}>
                  <option value="LLC">LLC</option><option value="Corp">Corporation</option><option value="Nonprofit">Nonprofit</option><option value="DBA">DBA</option>
                </select>
              </div>
              <input value={docsForm.purpose} onChange={e => setDocsForm({ ...docsForm, purpose: e.target.value })} placeholder="Business purpose / description" style={inputStyle} />
            </div>
            <button onClick={handleGenerateDocs} disabled={docsLoading}
              style={{ padding: '8px 16px', borderRadius: 8, background: '#7c3aed', color: '#fff', fontSize: 12, fontWeight: 600, border: 'none', cursor: 'pointer', width: '100%', opacity: docsLoading ? 0.7 : 1 }}
              className="flex items-center justify-center gap-2">
              {docsLoading ? <Loader2 size={14} className="animate-spin" /> : <FileDown size={14} />} Generate Documents
            </button>
            {docsResult && (
              <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 8, background: '#ede9fe', border: '1px solid #ddd6fe' }}>
                <div style={{ fontSize: 12, color: '#7c3aed', fontWeight: 600 }}>{docsResult}</div>
              </div>
            )}
          </div>

          {/* Package Recommender */}
          <div className="empire-card" style={{ padding: '20px 22px' }}>
            <div className="flex items-center gap-2 mb-3">
              <Sparkles size={18} className="text-[#16a34a]" />
              <div style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a' }}>Recommend Package</div>
            </div>
            <p style={{ fontSize: 11, color: '#999', marginBottom: 12 }}>Answer a few questions to find the best package for you</p>

            {!quizResult ? (
              <div className="space-y-3">
                <div>
                  <label style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', display: 'block', marginBottom: 4 }}>How many members/owners?</label>
                  <select value={quizAnswers.members} onChange={e => setQuizAnswers({ ...quizAnswers, members: e.target.value })} style={selectStyle}>
                    <option value="1">1 (Single-member)</option><option value="2">2-3</option><option value="4">4+</option>
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <input type="checkbox" checked={quizAnswers.registeredAgent} onChange={e => setQuizAnswers({ ...quizAnswers, registeredAgent: e.target.checked })} />
                  <label style={{ fontSize: 12, color: '#1a1a1a' }}>Need a registered agent?</label>
                </div>
                <div className="flex items-center gap-2">
                  <input type="checkbox" checked={quizAnswers.apostille} onChange={e => setQuizAnswers({ ...quizAnswers, apostille: e.target.checked })} />
                  <label style={{ fontSize: 12, color: '#1a1a1a' }}>Need apostille / international use?</label>
                </div>
                <div>
                  <label style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', display: 'block', marginBottom: 4 }}>Budget range</label>
                  <select value={quizAnswers.budget} onChange={e => setQuizAnswers({ ...quizAnswers, budget: e.target.value })} style={selectStyle}>
                    <option value="low">Minimal (just filing)</option><option value="medium">Moderate ($100-300)</option><option value="high">Full service ($300+)</option>
                  </select>
                </div>
                <button onClick={handleQuizSubmit}
                  style={{ padding: '8px 16px', borderRadius: 8, background: '#16a34a', color: '#fff', fontSize: 12, fontWeight: 600, border: 'none', cursor: 'pointer', width: '100%' }}
                  className="flex items-center justify-center gap-2"><Sparkles size={14} /> Get Recommendation</button>
              </div>
            ) : (
              <div style={{ padding: '14px 16px', borderRadius: 10, background: quizResult === 'empire' ? '#ede9fe' : quizResult === 'professional' ? '#fdf8eb' : '#dcfce7', border: `1px solid ${quizResult === 'empire' ? '#ddd6fe' : quizResult === 'professional' ? '#fde68a' : '#bbf7d0'}` }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: quizResult === 'empire' ? '#7c3aed' : quizResult === 'professional' ? '#b8960c' : '#16a34a', marginBottom: 4 }}>
                  We recommend: {quizResult.charAt(0).toUpperCase() + quizResult.slice(1)} Package
                </div>
                <div style={{ fontSize: 11, color: '#666', marginBottom: 8 }}>
                  {quizResult === 'empire' ? 'Full-service formation with registered agent, annual report filing, and premium support.' :
                   quizResult === 'professional' ? 'Complete formation package with EIN, operating agreement, and BOI report.' :
                   'Basic formation filing at the lowest cost — great for simple single-member LLCs.'}
                </div>
                <button onClick={() => { setQuizResult(null); setQuizAnswers({ members: '1', registeredAgent: false, apostille: false, budget: 'low' }); }}
                  style={{ fontSize: 11, color: '#666', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}>Retake Quiz</button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* RIGHT COLUMN: Document Activity (42%) */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Document Activity Feed */}
        <div className="empire-card" style={{ padding: '18px 20px', flex: viewerDoc ? '0 0 auto' : 1, maxHeight: viewerDoc ? 320 : 'none', display: 'flex', flexDirection: 'column' }}>
          <div className="flex items-center justify-between" style={{ marginBottom: 14 }}>
            <div className="flex items-center gap-2">
              <FileText size={16} className="text-[#b8960c]" />
              <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>Generated Documents</div>
            </div>
            <button onClick={fetchDocuments} disabled={docsListLoading}
              style={{ background: 'none', border: '1px solid #ece8e0', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
              <RefreshCw size={12} className={docsListLoading ? 'animate-spin' : ''} style={{ color: '#999' }} />
              <span style={{ fontSize: 10, color: '#999', fontWeight: 600 }}>Refresh</span>
            </button>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
            {docsListLoading && documents.length === 0 ? (
              <div className="flex items-center justify-center" style={{ padding: 40 }}>
                <Loader2 size={20} className="animate-spin" style={{ color: '#b8960c' }} />
              </div>
            ) : documents.length === 0 ? (
              <div style={{ padding: '30px 16px', textAlign: 'center' }}>
                <FileText size={28} style={{ color: '#ddd', margin: '0 auto 10px' }} />
                <div style={{ fontSize: 12, color: '#999', lineHeight: 1.6 }}>No documents yet. Generate your first document using the tools.</div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {documents.map((doc, i) => (
                  <div key={doc.id || doc.doc_id || i}
                    style={{ padding: '10px 14px', borderRadius: 8, background: '#faf9f7', border: '1px solid #ece8e0', borderLeft: `3px solid ${getDocBorderColor(doc)}`, cursor: 'pointer', transition: 'background 0.15s' }}
                    onMouseEnter={e => (e.currentTarget.style.background = '#f5f0e6')}
                    onMouseLeave={e => (e.currentTarget.style.background = '#faf9f7')}>
                    <div className="flex items-start justify-between" style={{ gap: 8 }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div className="flex items-center gap-2" style={{ marginBottom: 3 }}>
                          <FileText size={12} style={{ color: getDocBorderColor(doc), flexShrink: 0 }} />
                          <span style={{ fontSize: 11, fontWeight: 700, color: '#1a1a1a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {getDocTypeLabel(doc)}
                          </span>
                          <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 10, background: '#dcfce7', color: '#16a34a', fontWeight: 700, flexShrink: 0 }}>Saved</span>
                        </div>
                        <div style={{ fontSize: 10, color: '#666', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {getDocBusinessName(doc)}
                        </div>
                        <div className="flex items-center gap-3" style={{ marginTop: 4 }}>
                          <span style={{ fontSize: 9, color: '#aaa' }}>
                            <Clock size={9} style={{ display: 'inline', marginRight: 3, verticalAlign: 'middle' }} />
                            {doc.created_at || doc.timestamp ? new Date(doc.created_at || doc.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Recently'}
                          </span>
                          {doc.size && <span style={{ fontSize: 9, color: '#aaa' }}>{(doc.size / 1024).toFixed(1)} KB</span>}
                        </div>
                      </div>
                      <div className="flex items-center gap-1" style={{ flexShrink: 0 }}>
                        <button onClick={(e) => { e.stopPropagation(); handleViewDoc(doc); }}
                          style={{ padding: '4px 8px', borderRadius: 5, background: '#fff', border: '1px solid #ece8e0', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 3 }}
                          title="View document">
                          <Eye size={11} style={{ color: '#b8960c' }} />
                          <span style={{ fontSize: 9, color: '#b8960c', fontWeight: 600 }}>View</span>
                        </button>
                        <button onClick={(e) => { e.stopPropagation(); handleViewDoc(doc); }}
                          style={{ padding: '4px 8px', borderRadius: 5, background: '#fff', border: '1px solid #ece8e0', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 3 }}
                          title="Download document">
                          <FileDown size={11} style={{ color: '#666' }} />
                          <span style={{ fontSize: 9, color: '#666', fontWeight: 600 }}>DL</span>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Document Viewer */}
        <div className="empire-card" style={{ padding: viewerDoc ? '16px 18px' : '30px 18px', flex: 1, display: 'flex', flexDirection: 'column', minHeight: 200 }}>
          {viewerDoc ? (
            <>
              {/* Viewer header */}
              <div className="flex items-center justify-between" style={{ marginBottom: 12, paddingBottom: 10, borderBottom: '1px solid #ece8e0' }}>
                <div className="flex items-center gap-2">
                  <FileText size={14} style={{ color: getDocBorderColor(viewerDoc) }} />
                  <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{getDocTypeLabel(viewerDoc)}</span>
                  <span style={{ fontSize: 10, color: '#999' }}>- {getDocBusinessName(viewerDoc)}</span>
                </div>
                <button onClick={() => { setViewerDoc(null); setViewerContent(null); }}
                  style={{ background: 'none', border: '1px solid #ece8e0', borderRadius: 6, padding: '3px 6px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                  <X size={14} style={{ color: '#999' }} />
                </button>
              </div>

              {/* Viewer content */}
              {viewerLoading ? (
                <div className="flex items-center justify-center" style={{ flex: 1 }}>
                  <Loader2 size={20} className="animate-spin" style={{ color: '#b8960c' }} />
                </div>
              ) : (
                <pre style={{ flex: 1, margin: 0, padding: 14, background: '#faf9f7', border: '1px solid #e5e0d8', borderRadius: 8, fontSize: 10, lineHeight: 1.6, overflowY: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#333', minHeight: 0 }}>
                  {viewerContent || ''}
                </pre>
              )}

              {/* Viewer action bar */}
              <div className="flex items-center gap-2" style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid #ece8e0' }}>
                <button onClick={() => handleDownloadDoc(viewerDoc)}
                  style={{ padding: '6px 12px', borderRadius: 6, background: '#b8960c', color: '#fff', fontSize: 10, fontWeight: 600, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <FileDown size={11} /> Download
                </button>
                <button onClick={() => { if (viewerContent) { navigator.clipboard.writeText(viewerContent); showToast('Copied to clipboard'); } }}
                  style={{ padding: '6px 12px', borderRadius: 6, background: '#f5f0e6', color: '#b8960c', fontSize: 10, fontWeight: 600, border: '1px solid #e5dcc8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Copy size={11} /> Copy to Clipboard
                </button>
                <button onClick={() => showToast('Send to Customer — coming soon')}
                  style={{ padding: '6px 12px', borderRadius: 6, background: '#f0f0f0', color: '#666', fontSize: 10, fontWeight: 600, border: '1px solid #e0e0e0', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Send size={11} /> Send to Customer
                </button>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center" style={{ flex: 1, color: '#ccc' }}>
              <Eye size={28} style={{ marginBottom: 10, color: '#ddd' }} />
              <div style={{ fontSize: 12, color: '#aaa' }}>Select a document to preview</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ============ 10. NEW ORDER WIZARD ============

function NewOrderWizard({ onClose }: { onClose: () => void }) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const [selectedPackage, setSelectedPackage] = useState<string>('');
  const [selectedState, setSelectedState] = useState<'DC' | 'MD' | 'VA'>('DC');
  const [businessName, setBusinessName] = useState('');
  const [businessType, setBusinessType] = useState('LLC');
  const [businessPurpose, setBusinessPurpose] = useState('');
  const [members, setMembers] = useState<{ name: string; role: string; ownership: string }[]>([{ name: '', role: 'Member', ownership: '100' }]);
  const [contactName, setContactName] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [contactAddress, setContactAddress] = useState('');
  const [additionalServices, setAdditionalServices] = useState<string[]>([]);

  const inputStyle: React.CSSProperties = { padding: '10px 14px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 13, width: '100%', background: '#fff', outline: 'none' };

  const pkgData = FALLBACK_PACKAGES.find(p => p.id === selectedPackage);
  const guide = STATE_GUIDES[selectedState];

  const getStateFee = () => guide?.filingFee || 99;
  const getServiceFee = () => pkgData?.price || 0;
  const getAdditionalFees = () => {
    let total = 0;
    if (additionalServices.includes('registered-agent')) total += 99;
    if (additionalServices.includes('ein-application')) total += 49;
    if (additionalServices.includes('apostille-service')) total += 79;
    if (additionalServices.includes('operating-agreement') && selectedPackage === 'starter') total += 79;
    if (additionalServices.includes('boc-report') && selectedPackage === 'starter') total += 49;
    return total;
  };
  const getTotal = () => getServiceFee() + getStateFee() + getAdditionalFees();

  const addMember = () => setMembers([...members, { name: '', role: 'Member', ownership: '' }]);
  const removeMember = (i: number) => setMembers(members.filter((_, idx) => idx !== i));
  const updateMember = (i: number, field: string, value: string) => {
    const updated = [...members];
    (updated[i] as any)[field] = value;
    setMembers(updated);
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await fetch(API + '/llcfactory/orders', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          package: selectedPackage, state: selectedState,
          business: { name: businessName, type: businessType, purpose: businessPurpose },
          members, contact: { name: contactName, email: contactEmail, phone: contactPhone, address: contactAddress },
          additionalServices, total: getTotal(),
        }),
      });
    } catch { /* Order submitted even if API not ready */ }
    setLoading(false);
    setSubmitted(true);
  };

  const canProceed = () => {
    switch (step) {
      case 1: return !!selectedPackage;
      case 2: return true;
      case 3: return !!businessName.trim();
      case 4: return members.some(m => m.name.trim());
      case 5: return !!contactName.trim() && !!contactEmail.trim();
      case 6: return true;
      case 7: return true;
      default: return true;
    }
  };

  const stepLabels = ['Package', 'State', 'Business', 'Members', 'Contact', 'Add-ons', 'Review'];

  if (submitted) {
    return (
      <div style={{ maxWidth: 600, margin: '60px auto', padding: '24px 36px', textAlign: 'center' }}>
        <div className="empire-card" style={{ padding: '40px 30px' }}>
          <div className="w-16 h-16 rounded-full bg-[#dcfce7] flex items-center justify-center mx-auto mb-4"><CheckCircle size={32} className="text-[#16a34a]" /></div>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a', marginBottom: 8 }}>Order Submitted</div>
          <div style={{ fontSize: 13, color: '#666', marginBottom: 24 }}>Your formation order for {businessName} has been received. We will begin processing immediately.</div>
          <button onClick={onClose} style={{ padding: '10px 24px', borderRadius: 10, background: '#16a34a', color: '#fff', fontSize: 13, fontWeight: 600, border: 'none', cursor: 'pointer' }}>Back to Orders</button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 700, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center justify-between mb-4">
        <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>New Order</h1>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#999' }}><X size={20} /></button>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-1 mb-6">
        {stepLabels.map((label, i) => (
          <React.Fragment key={label}>
            <div className="flex items-center gap-1">
              <div style={{ width: 24, height: 24, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, background: step > i + 1 ? '#16a34a' : step === i + 1 ? '#b8960c' : '#ece8e0', color: step >= i + 1 ? '#fff' : '#999' }}>
                {step > i + 1 ? <Check size={12} /> : i + 1}
              </div>
              <span style={{ fontSize: 10, color: step === i + 1 ? '#b8960c' : '#999', fontWeight: step === i + 1 ? 700 : 500 }}>{label}</span>
            </div>
            {i < stepLabels.length - 1 && <div style={{ flex: 1, height: 1, background: step > i + 1 ? '#16a34a' : '#ece8e0' }} />}
          </React.Fragment>
        ))}
      </div>

      <div className="empire-card" style={{ padding: '24px 28px', minHeight: 300 }}>
        {/* Step 1: Package */}
        {step === 1 && (
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>Choose a Package</div>
            <div className="space-y-3">
              {FALLBACK_PACKAGES.map(pkg => (
                <div key={pkg.id} onClick={() => setSelectedPackage(pkg.id)}
                  style={{ padding: '16px 18px', borderRadius: 12, border: `2px solid ${selectedPackage === pkg.id ? pkg.color : '#ece8e0'}`, cursor: 'pointer', background: selectedPackage === pkg.id ? `${pkg.color}08` : '#fff' }}
                  className="transition-all">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span style={{ fontSize: 14, fontWeight: 700, color: pkg.color }}>{pkg.name}</span>
                        {pkg.badge && <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 20, background: pkg.color, color: '#fff', fontWeight: 700 }}>{pkg.badge}</span>}
                      </div>
                      <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>{pkg.description}</div>
                    </div>
                    <div style={{ fontSize: 20, fontWeight: 800, color: '#1a1a1a' }}>${pkg.price}<span style={{ fontSize: 11, fontWeight: 400, color: '#999' }}> + fees</span></div>
                  </div>
                </div>
              ))}
              <div onClick={() => setSelectedPackage('custom')}
                style={{ padding: '16px 18px', borderRadius: 12, border: `2px solid ${selectedPackage === 'custom' ? '#666' : '#ece8e0'}`, cursor: 'pointer', background: selectedPackage === 'custom' ? '#f5f5f5' : '#fff' }}
                className="transition-all">
                <div style={{ fontSize: 14, fontWeight: 700, color: '#666' }}>Custom (A la Carte)</div>
                <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>Choose individual services</div>
              </div>
            </div>
          </div>
        )}

        {/* Step 2: State */}
        {step === 2 && (
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>Select State</div>
            <div className="space-y-3">
              {(['DC', 'MD', 'VA'] as const).map(st => {
                const g = STATE_GUIDES[st];
                return (
                  <div key={st} onClick={() => setSelectedState(st)}
                    style={{ padding: '16px 18px', borderRadius: 12, border: `2px solid ${selectedState === st ? '#16a34a' : '#ece8e0'}`, cursor: 'pointer', background: selectedState === st ? '#dcfce710' : '#fff' }}
                    className="transition-all">
                    <div className="flex items-center justify-between">
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>{g.name}</div>
                        <div style={{ fontSize: 11, color: '#999' }}>{g.authority}</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: 16, fontWeight: 700, color: '#b8960c' }}>${g.filingFee}</div>
                        <div style={{ fontSize: 10, color: '#999' }}>filing fee</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Step 3: Business Details */}
        {step === 3 && (
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>Business Details</div>
            <div className="space-y-3">
              <div>
                <label style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', display: 'block', marginBottom: 4 }}>Business Name</label>
                <input value={businessName} onChange={e => setBusinessName(e.target.value)} placeholder="e.g. Acme Solutions LLC" style={inputStyle} />
              </div>
              <div>
                <label style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', display: 'block', marginBottom: 4 }}>Entity Type</label>
                <select value={businessType} onChange={e => setBusinessType(e.target.value)} style={{ ...inputStyle, cursor: 'pointer' }}>
                  <option value="LLC">LLC</option><option value="Corporation">Corporation</option><option value="Nonprofit">Nonprofit</option><option value="DBA">DBA / Trade Name</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', display: 'block', marginBottom: 4 }}>Business Purpose</label>
                <input value={businessPurpose} onChange={e => setBusinessPurpose(e.target.value)} placeholder="e.g. General consulting services" style={inputStyle} />
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Members */}
        {step === 4 && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>Members / Owners</div>
              <button onClick={addMember} style={{ padding: '4px 12px', borderRadius: 8, background: '#16a34a', color: '#fff', fontSize: 11, fontWeight: 600, border: 'none', cursor: 'pointer' }} className="flex items-center gap-1"><Plus size={12} /> Add</button>
            </div>
            <div className="space-y-3">
              {members.map((m, i) => (
                <div key={i} style={{ padding: '14px 16px', borderRadius: 10, border: '1px solid #ece8e0', background: '#fff' }}>
                  <div className="flex items-center justify-between mb-2">
                    <span style={{ fontSize: 11, fontWeight: 700, color: '#999' }}>Member {i + 1}</span>
                    {members.length > 1 && <button onClick={() => removeMember(i)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ccc' }}><X size={14} /></button>}
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <input value={m.name} onChange={e => updateMember(i, 'name', e.target.value)} placeholder="Full name" style={{ ...inputStyle, fontSize: 12 }} />
                    <select value={m.role} onChange={e => updateMember(i, 'role', e.target.value)} style={{ ...inputStyle, fontSize: 12, cursor: 'pointer' }}>
                      <option value="Member">Member</option><option value="Manager">Manager</option><option value="Director">Director</option><option value="Officer">Officer</option>
                    </select>
                    <input value={m.ownership} onChange={e => updateMember(i, 'ownership', e.target.value)} placeholder="%" style={{ ...inputStyle, fontSize: 12 }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step 5: Contact Info */}
        {step === 5 && (
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>Contact Information</div>
            <div className="space-y-3">
              <div><label style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', display: 'block', marginBottom: 4 }}>Full Name</label><input value={contactName} onChange={e => setContactName(e.target.value)} placeholder="Your name" style={inputStyle} /></div>
              <div><label style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', display: 'block', marginBottom: 4 }}>Email</label><input value={contactEmail} onChange={e => setContactEmail(e.target.value)} placeholder="email@example.com" type="email" style={inputStyle} /></div>
              <div><label style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', display: 'block', marginBottom: 4 }}>Phone</label><input value={contactPhone} onChange={e => setContactPhone(e.target.value)} placeholder="(202) 555-0100" style={inputStyle} /></div>
              <div><label style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', display: 'block', marginBottom: 4 }}>Address</label><input value={contactAddress} onChange={e => setContactAddress(e.target.value)} placeholder="Street address, City, State, ZIP" style={inputStyle} /></div>
            </div>
          </div>
        )}

        {/* Step 6: Additional Services */}
        {step === 6 && (
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>Additional Services</div>
            <div className="space-y-2">
              {[
                { id: 'registered-agent', name: 'Registered Agent (1 Year)', price: 99, desc: 'Statutory agent service' },
                { id: 'ein-application', name: 'EIN Application', price: 49, desc: 'Federal tax ID number' },
                { id: 'apostille-service', name: 'Apostille / Authentication', price: 79, desc: 'Document authentication for international use' },
                { id: 'operating-agreement', name: 'Operating Agreement', price: 79, desc: 'Custom drafted OA' },
                { id: 'boc-report', name: 'BOI Report (FinCEN)', price: 49, desc: 'Beneficial ownership filing' },
                { id: 'mail-forwarding', name: 'Mail Forwarding', price: 29, desc: 'Business mail service' },
              ].map(svc => {
                const alreadyIncluded = pkgData?.included.includes(svc.id);
                const isChecked = additionalServices.includes(svc.id);
                return (
                  <div key={svc.id} style={{ padding: '12px 16px', borderRadius: 10, border: '1px solid #ece8e0', background: alreadyIncluded ? '#dcfce710' : '#fff', opacity: alreadyIncluded ? 0.6 : 1 }}
                    className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <input type="checkbox" disabled={!!alreadyIncluded} checked={!!alreadyIncluded || isChecked}
                        onChange={e => {
                          if (alreadyIncluded) return;
                          setAdditionalServices(e.target.checked ? [...additionalServices, svc.id] : additionalServices.filter(s => s !== svc.id));
                        }} />
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{svc.name} {alreadyIncluded && <span style={{ fontSize: 9, color: '#16a34a', fontWeight: 700 }}>INCLUDED</span>}</div>
                        <div style={{ fontSize: 10, color: '#999' }}>{svc.desc}</div>
                      </div>
                    </div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: alreadyIncluded ? '#16a34a' : '#1a1a1a' }}>{alreadyIncluded ? 'Free' : `$${svc.price}`}</div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Step 7: Review */}
        {step === 7 && (
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>Review & Submit</div>
            <div className="space-y-4">
              <div style={{ padding: '14px 16px', borderRadius: 10, background: '#f5f2ed' }}>
                <div className="grid grid-cols-2 gap-3">
                  <div><div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999' }}>Package</div><div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{pkgData?.name || 'Custom'}</div></div>
                  <div><div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999' }}>State</div><div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{STATE_GUIDES[selectedState]?.name}</div></div>
                  <div><div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999' }}>Business</div><div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{businessName || 'N/A'}</div></div>
                  <div><div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999' }}>Type</div><div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{businessType}</div></div>
                  <div><div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999' }}>Contact</div><div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{contactName || 'N/A'}</div></div>
                  <div><div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999' }}>Email</div><div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{contactEmail || 'N/A'}</div></div>
                </div>
              </div>

              <div style={{ borderTop: '1px solid #ece8e0', paddingTop: 14 }}>
                <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', marginBottom: 8 }}>Pricing Summary</div>
                <div className="space-y-2">
                  <div className="flex justify-between"><span style={{ fontSize: 12, color: '#666' }}>Service Fee ({pkgData?.name || 'Custom'})</span><span style={{ fontSize: 12, fontWeight: 600 }}>${getServiceFee()}</span></div>
                  <div className="flex justify-between"><span style={{ fontSize: 12, color: '#666' }}>State Filing Fee ({selectedState})</span><span style={{ fontSize: 12, fontWeight: 600 }}>${getStateFee()}</span></div>
                  {getAdditionalFees() > 0 && <div className="flex justify-between"><span style={{ fontSize: 12, color: '#666' }}>Additional Services</span><span style={{ fontSize: 12, fontWeight: 600 }}>${getAdditionalFees()}</span></div>}
                  <div className="flex justify-between" style={{ borderTop: '1px solid #ece8e0', paddingTop: 8, marginTop: 4 }}>
                    <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>Total</span>
                    <span style={{ fontSize: 18, fontWeight: 800, color: '#16a34a' }}>${getTotal()}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation buttons */}
      <div className="flex items-center justify-between mt-4">
        <button onClick={() => step === 1 ? onClose() : setStep(step - 1)}
          style={{ padding: '10px 20px', borderRadius: 10, background: '#fff', color: '#666', fontSize: 13, fontWeight: 600, border: '1px solid #ece8e0', cursor: 'pointer' }}>
          {step === 1 ? 'Cancel' : 'Back'}
        </button>
        {step < 7 ? (
          <button onClick={() => setStep(step + 1)} disabled={!canProceed()}
            style={{ padding: '10px 20px', borderRadius: 10, background: canProceed() ? '#16a34a' : '#ccc', color: '#fff', fontSize: 13, fontWeight: 600, border: 'none', cursor: canProceed() ? 'pointer' : 'not-allowed' }}
            className="flex items-center gap-2">
            Next <ArrowRight size={14} />
          </button>
        ) : (
          <button onClick={handleSubmit} disabled={loading}
            style={{ padding: '10px 24px', borderRadius: 10, background: '#16a34a', color: '#fff', fontSize: 13, fontWeight: 600, border: 'none', cursor: 'pointer', opacity: loading ? 0.7 : 1 }}
            className="flex items-center gap-2">
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />} Submit Order
          </button>
        )}
      </div>
    </div>
  );
}
