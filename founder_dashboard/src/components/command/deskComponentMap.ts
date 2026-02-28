import { DeskId } from '@/lib/deskData';
import OperationsDesk from '../desks/OperationsDesk';
import FinanceDesk from '../desks/FinanceDesk';
import SalesDesk from '../desks/SalesDesk';
import DesignDesk from '../desks/DesignDesk';
import EstimatingDesk from '../desks/EstimatingDesk';
import ClientsDesk from '../desks/ClientsDesk';
import ContractorsDesk from '../desks/ContractorsDesk';
import SupportDesk from '../desks/SupportDesk';
import MarketingDesk from '../desks/MarketingDesk';
import WebsiteDesk from '../desks/WebsiteDesk';
import ITDesk from '../desks/ITDesk';
import LegalDesk from '../desks/LegalDesk';
import LabDesk from '../desks/LabDesk';

export const DESK_COMPONENTS: Record<DeskId, React.ComponentType> = {
  operations:  OperationsDesk,
  finance:     FinanceDesk,
  sales:       SalesDesk,
  design:      DesignDesk,
  estimating:  EstimatingDesk,
  clients:     ClientsDesk,
  contractors: ContractorsDesk,
  support:     SupportDesk,
  marketing:   MarketingDesk,
  website:     WebsiteDesk,
  it:          ITDesk,
  legal:       LegalDesk,
  lab:         LabDesk,
};
