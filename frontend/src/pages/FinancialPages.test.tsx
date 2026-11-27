import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { renderHook } from '@testing-library/react';
import ExpensesPage from './ExpensesPage';
import AddExpensePage from './AddExpensePage';
import BalancesPage from './BalancesPage';
import PaymentRequestsPage from './PaymentRequestsPage';
import CreatePaymentRequestPage from './CreatePaymentRequestPage';
import { useGroupFinances } from '../hooks/useGroupFinances';
const {request} = vi.hoisted(()=>({request:vi.fn()}));
vi.mock('../hooks/useApi',()=>({useApi:()=>({request})}));
vi.mock('../context/ThemeContext',()=>({useTheme:()=>({resolvedTheme:'light'})}));
vi.mock('../components/background/WavyBackground',()=>({default:()=>null}));
vi.mock('../components/layout/AppSidebar',()=>({default:()=>null}));
vi.mock('../components/layout/AppHeader',()=>({default:()=>null}));
vi.mock('recharts',()=>{const Empty=()=>null;return {Area:Empty,AreaChart:Empty,CartesianGrid:Empty,Cell:Empty,Pie:Empty,PieChart:Empty,ResponsiveContainer:Empty,Tooltip:Empty,XAxis:Empty,YAxis:Empty,Legend:Empty};});
const date='2026-11-26T12:00:00Z';
const group={id:7,name:'Test household',category:'Home',custom_category:null,currency:'USD',default_split:'Equal',color:'#4a7856',created_by:1,created_at:date,description:null};
const members=[{id:1,group_id:7,user_id:1,full_name:'Alice Example',role:'owner',joined_at:date},{id:2,group_id:7,user_id:2,full_name:'Bob Example',role:'member',joined_at:date}];
const expense={id:10,group_id:7,paid_by:1,description:'Weekly groceries',amount:'100.00',category:'Groceries',expense_date:'2026-11-26',reference:null,split_method:'Equal',created_at:date,splits:[{id:1,expense_id:10,user_id:1,amount_owed:'50.00'},{id:2,expense_id:10,user_id:2,amount_owed:'50.00'}]};
const payment={id:20,group_id:7,from_user_id:2,to_user_id:1,amount:'15.00',status:'pending',created_at:date,confirmed_at:null};
const paymentRequest={id:30,group_id:7,requester_id:1,debtor_id:2,amount:'40.00',fulfilled_amount:'15.00',description:'Groceries repayment',status:'pending',created_at:date,resolved_at:null,due_date:null};
let user:number; let requests:unknown[]; let payments:typeof payment[]; let fail:boolean;
beforeEach(()=>{user=1;requests=[];payments=[];fail=false;request.mockReset();request.mockImplementation(async(path:string,options?:RequestInit)=>{
 if(path==='/users/me')return {id:user}; if(path==='/groups')return [group]; if(path==='/groups/7/members')return members;
 if(options?.method==='POST')return {id:99};
 if(path==='/groups/7/expenses'){if(fail)throw new Error('Financial network failure');return [expense];}
 if(path==='/groups/7/payments')return payments;
 if(path==='/groups/7/payment-requests')return requests;
 if(path==='/groups/7/balances')return {group_id:7,balances:[{user_id:1,net_balance:'50.00'},{user_id:2,net_balance:'-50.00'}]};
 if(path==='/groups/7/settlements')return {group_id:7,settlements:[{from_user_id:2,to_user_id:1,amount:'50.00'}]};
 throw new Error(`Unexpected ${path}`);
});});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
function posts(path:string){return request.mock.calls.filter(([p,o])=>p===path&&o?.method==='POST');}
function change(label:RegExp,value:string){fireEvent.change(screen.getByLabelText(label),{target:{value}});}
async function expenseForm(){render(<MemoryRouter><AddExpensePage/></MemoryRouter>);await screen.findByRole('option',{name:/Test household/});change(/Target group/i,'7');change(/^Description$/i,'Dinner');change(/Total Amount/i,'100');}
async function requestForm(){render(<MemoryRouter><CreatePaymentRequestPage/></MemoryRouter>);await screen.findByRole('option',{name:/Test household/});change(/Target Group/i,'7');change(/Recipient Member/i,'2');change(/Requested Amount/i,'40');}
describe('Financial integration',()=>{
 it('loads real expenses and split details',async()=>{render(<MemoryRouter><ExpensesPage/></MemoryRouter>);await screen.findByText('Weekly groceries');fireEvent.click(screen.getByRole('button',{name:'View Split'}));expect(within(screen.getByRole('dialog')).getByText('Bob Example')).toBeTruthy();fireEvent.click(screen.getByRole('button',{name:'Close Breakdown'}));change(/Filter expenses/i,'missing');expect(screen.queryByText('Weekly groceries')).toBeNull();});
 it.each(['equal','exact','percentage'])('submits %s expense allocations',async(mode)=>{await expenseForm();if(mode==='exact'){fireEvent.click(screen.getByRole('button',{name:'Exact Amounts'}));change(/Alice Example share/i,'30');change(/Bob Example share/i,'70');}if(mode==='percentage'){fireEvent.click(screen.getByRole('button',{name:'Percentages'}));change(/Alice Example percentage/i,'30');change(/Bob Example percentage/i,'70');}fireEvent.click(screen.getByRole('button',{name:/Save & Record Expense/}));await waitFor(()=>expect(posts('/groups/7/expenses')).toHaveLength(1));const options=posts('/groups/7/expenses')[0][1];expect(JSON.parse(options.body)).toMatchObject({amount:'100.00',split_method:mode==='equal'?'Equal':mode==='exact'?'Exact':'Percent',splits:[{user_id:1,amount_owed:mode==='equal'?'50.00':'30.00'},{user_id:2,amount_owed:mode==='equal'?'50.00':'70.00'}]});expect(new Headers(options.headers).get('Idempotency-Key')).toBeTruthy();});
 it('blocks excessive request and submits valid request',async()=>{await requestForm();change(/Requested Amount/i,'51');const button=screen.getByRole('button',{name:'Create Payment Request'});expect((button as HTMLButtonElement).disabled).toBe(true);change(/Requested Amount/i,'40');fireEvent.click(button);await waitFor(()=>expect(posts('/groups/7/payment-requests')).toHaveLength(1));expect(JSON.parse(posts('/groups/7/payment-requests')[0][1].body)).toMatchObject({debtor_id:2,amount:'40.00'});});
 it('shows partial fulfillment and cancels outgoing request',async()=>{requests=[paymentRequest];vi.spyOn(window,'confirm').mockReturnValue(true);render(<MemoryRouter><PaymentRequestsPage/></MemoryRouter>);const row=await screen.findByRole('row',{name:/Groceries repayment/});expect(within(row).getByText('$25.00')).toBeTruthy();fireEvent.click(within(row).getByRole('button',{name:'Cancel request'}));await waitFor(()=>expect(posts('/groups/7/payment-requests/30/cancel')).toHaveLength(1));});
 it('does not allow debtor to cancel incoming request',async()=>{user=2;requests=[paymentRequest];render(<MemoryRouter><PaymentRequestsPage/></MemoryRouter>);await screen.findByText('Groceries repayment');expect(screen.queryByRole('button',{name:'Cancel request'})).toBeNull();expect(screen.getByRole('button',{name:'View balances'})).toBeTruthy();});
 it.each(['confirm','reject'])('allows recipient to %s pending payment',async(action)=>{payments=[payment];vi.spyOn(window,'confirm').mockReturnValue(true);render(<MemoryRouter><BalancesPage/></MemoryRouter>);fireEvent.click(await screen.findByRole('button',{name:new RegExp(`^${action}$`,'i')}));await waitFor(()=>expect(posts(`/groups/7/payments/20/${action}`)).toHaveLength(1));});
 it('records suggested settlement as debtor',async()=>{user=2;vi.spyOn(window,'confirm').mockReturnValue(true);render(<MemoryRouter><BalancesPage/></MemoryRouter>);fireEvent.click(await screen.findByRole('button',{name:'Record Settlement'}));await waitFor(()=>expect(posts('/groups/7/payments')).toHaveLength(1));expect(JSON.parse(posts('/groups/7/payments')[0][1].body)).toEqual({to_user_id:1,amount:'50.00'});});
 it('reuses expense key on failed submission and blocks rapid duplicate',async()=>{const base=request.getMockImplementation()!;let reject!:(e:Error)=>void;request.mockImplementation((path:string,options?:RequestInit)=>path==='/groups/7/expenses'&&options?.method==='POST'?new Promise((_,r)=>{reject=r;}):base(path,options));await expenseForm();const button=screen.getByRole('button',{name:/Save & Record Expense/});act(()=>{fireEvent.click(button);fireEvent.click(button);});expect(posts('/groups/7/expenses')).toHaveLength(1);await act(async()=>reject(new Error('Retry needed')));await screen.findByText('Retry needed');fireEvent.click(screen.getByRole('button',{name:/Save & Record Expense/}));expect(posts('/groups/7/expenses')).toHaveLength(2);expect(new Headers(posts('/groups/7/expenses')[0][1].headers).get('Idempotency-Key')).toBe(new Headers(posts('/groups/7/expenses')[1][1].headers).get('Idempotency-Key'));await act(async()=>reject(new Error('Retry needed')));});
 it('loads balances and recovers from financial fetch failure',async()=>{fail=true;const {result}=renderHook(()=>useGroupFinances());await waitFor(()=>expect(result.current.error).toBe('Financial network failure'));expect(result.current.groups).toEqual([]);fail=false;act(()=>result.current.reload());await waitFor(()=>expect(result.current.isLoading).toBe(false));expect(result.current.groups[0].balances).toEqual([{user_id:1,net_balance:'50.00'},{user_id:2,net_balance:'-50.00'}]);});
});
