import csv
import io
import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from urllib.error import URLError
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase,override_settings
from django.urls import reverse
from django.utils import timezone
from .forms import EvidenceForm,QuantityFormSet,VariantForm
from .models import Project,Product,Variant,Component,Evidence,PlanVersion
from .research import canonical_url,evidence_report,run_research
from .services import load_project,cost,demand,evaluate,propose,save_version,sales_scenario

class PlanningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user=get_user_model().objects.create_user('planner-owner',is_staff=True)
        cls.operator=get_user_model().objects.create_user('planner-operator')
        today=timezone.localdate()
        cls.project=Project.objects.create(name='Plan de prueba',launch_date=today+timedelta(days=30),sell_by=today+timedelta(days=59),budget=1000,reserve=100,fixed_costs=100)
        cls.product=Product.objects.create(project=cls.project,name='Blusa',unit_cost=20,cost_confirmed=True,material_available=True,minimum_model=10,minimum_color=5,multiple=5,capacity=60,lead_days=10,retail_price=40,wholesale_price=30)
        cls.first=Variant.objects.create(product=cls.product,color='Negro',size='M',stock=10,target=30)
        cls.second=Variant.objects.create(product=cls.product,color='Negro',size='L',stock=0,target=20)
    def setUp(self):self.client.force_login(self.user)
    def plan(self):return load_project(self.project.pk)
    def quantities_payload(self,**updates):
        variants=list(Variant.objects.filter(product__project=self.project))
        data={'variants-TOTAL_FORMS':str(len(variants)),'variants-INITIAL_FORMS':str(len(variants)),'variants-MIN_NUM_FORMS':'0','variants-MAX_NUM_FORMS':'1000'}
        for i,v in enumerate(variants):
            data.update({f'variants-{i}-id':str(v.pk),f'variants-{i}-stock':str(v.stock),f'variants-{i}-target':str(v.target) if v.target is not None else '',f'variants-{i}-quantity':str(v.quantity)})
            if v.locked:data[f'variants-{i}-locked']='on'
        data.update(updates);return data
    def test_cost_complete_or_components_never_both_and_waste_once(self):
        Component.objects.create(product=self.product,name='Tela',quantity='1.2',unit_price=10,waste=10)
        Component.objects.create(product=self.product,name='Confección',quantity=1,unit='prenda',unit_price=8,waste=0)
        self.assertEqual(cost(self.product),Decimal('20'))
        self.product.cost_mode='components';self.product.save()
        self.assertEqual(cost(self.product),Decimal('21.2000'))
        result=evaluate(self.plan(),quantities={self.first.pk:10,self.second.pk:10})
        self.assertEqual(result['variable'],Decimal('424.00'))
        self.assertEqual(result['required'],Decimal('624.00'))
        self.assertEqual(result['full_unit_cost'],Decimal('26.20'))
    def test_three_proposals_respect_budget_multiples_stock_capacity(self):
        units=[]
        for factor in [Decimal('.60'),Decimal('1'),Decimal('1.30')]:
            result=propose(self.plan(),factor)
            self.assertTrue(result['feasible'],result['errors'])
            self.assertLessEqual(result['required'],self.project.budget)
            self.assertLessEqual(result['units'],self.product.capacity)
            self.assertTrue(all(r['quantity']%5==0 for r in result['rows']))
            units.append(result['units'])
        self.assertEqual(units,[25,40,40])
        balanced=propose(self.plan(),Decimal('1'))
        self.assertEqual(balanced['rows'][0]['quantity'],20)
        self.assertEqual(balanced['existing_stock'],10)
    def test_minimum_infeasible_does_not_overspend(self):
        self.project.budget=210;self.project.save()
        result=propose(self.plan(),Decimal('1'))
        self.assertFalse(result['feasible']);self.assertEqual(result['units'],0)
        self.assertEqual(result['required'],Decimal('200.00'))
        self.assertTrue(any('No existe' in error for error in result['errors']))
    def test_locked_conflicts_are_preserved_and_explained(self):
        self.first.quantity=50;self.first.locked=True;self.first.save()
        result=propose(self.plan(),Decimal('.60'))
        self.assertEqual(result['rows'][0]['quantity'],50)
        self.assertFalse(result['feasible'])
        self.assertTrue(any('Presupuesto insuficiente' in error for error in result['errors']))
    def test_missing_cost_unavailable_color_and_late_delivery(self):
        for field,value in [('unit_cost',None),('material_available',False),('lead_days',40),('capacity',0)]:
            original=getattr(self.product,field);setattr(self.product,field,value);self.product.save()
            result=propose(self.plan(),Decimal('1'))
            self.assertEqual(result['units'],0)
            self.assertFalse(result['feasible'])
            setattr(self.product,field,original);self.product.save()
        self.first.available=False;self.first.save()
        result=propose(self.plan(),Decimal('1'))
        self.assertEqual(result['rows'][0]['quantity'],0)
    def test_stock_covers_targets_and_unknown_demand_does_not_reproduce_stock(self):
        for v in [self.first,self.second]:v.stock=100;v.target=None;v.save()
        result=propose(self.plan(),Decimal('1'))
        self.assertEqual(result['units'],0)
    def test_demand_uses_available_days_latest_period_and_not_inquiries(self):
        self.first.target=None;self.first.save()
        today=timezone.localdate()
        for kind,units,end,days in [('sales',100,today-timedelta(days=5),10),('sales',10,today,5),('inquiries',10000,today,5)]:
            Evidence.objects.create(project=self.project,product=self.product,variant=self.first,kind=kind,title=kind,units=units,days_in_stock=days,period_start=end-timedelta(days=9),period_end=end,signal='Dato de prueba')
        target,reason,confidence=demand(self.plan(),self.first)
        self.assertEqual(target,60);self.assertIn('Solo el periodo más reciente',reason);self.assertIn('Media',confidence)
        Evidence.objects.filter(kind='sales').update(days_in_stock=0)
        self.assertIsNone(demand(self.plan(),self.first)[0])
    def test_manual_constraints_report_model_color_and_multiple(self):
        self.product.minimum_color=10;self.product.save()
        self.second.color='Marfil';self.second.save()
        result=evaluate(self.plan(),quantities={self.first.pk:5,self.second.pk:6})
        self.assertFalse(result['feasible'])
        self.assertTrue(any('mínimo por color' in e for e in result['errors']))
        self.assertTrue(any('múltiplo' in e for e in result['errors']))
    def test_money_rounding_and_boundary_budgets(self):
        self.product.unit_cost=Decimal('.005');self.product.multiple=1;self.product.minimum_model=1;self.product.minimum_color=1;self.product.save()
        result=evaluate(self.plan(),quantities={self.first.pk:1,self.second.pk:1})
        self.assertEqual(result['variable'],Decimal('.02'))
        for budget in [0,100,199,200,201,210,300,1000]:
            self.project.budget=budget;self.project.save()
            result=propose(self.plan(),Decimal('1.3'))
            if budget>=200:self.assertLessEqual(result['required'],Decimal(budget))
            else:self.assertFalse(result['feasible'])
    def test_sales_scenario_separates_gross_cash_and_remaining_stock(self):
        result=evaluate(self.plan(),quantities={self.first.pk:10,self.second.pk:10})
        scenario=sales_scenario(self.plan(),result,50)
        self.assertEqual(scenario['sold'],10)
        self.assertEqual(scenario['recovered'],Decimal('400.00'))
        self.assertEqual(scenario['invested'],Decimal('500.00'))
        self.assertEqual(scenario['cash_difference'],Decimal('-100.00'))
        self.assertEqual(scenario['gross_result'],Decimal('100.00'))
        self.assertEqual(scenario['remaining_stock_value'],Decimal('200.00'))
        self.assertEqual(scenario['margins'][0]['margin'],Decimal('50.00'))
        self.assertEqual(scenario['margins'][0]['markup'],Decimal('100.00'))
    def test_partial_cost_does_not_appear_as_valid_full_cost(self):
        self.product.unit_cost=None;self.product.save()
        result=evaluate(self.plan(),quantities={self.first.pk:10})
        self.assertFalse(result['costs_complete']);self.assertFalse(result['feasible'])
        self.assertIsNone(result['rows'][0]['total']);self.assertIsNone(result['full_unit_cost'])
        self.assertFalse(sales_scenario(self.plan(),result,50)['complete'])

    def test_cent_rounding_reconciles_stock_and_gross_vs_cash(self):
        self.product.unit_cost=Decimal('.005');self.product.save()
        result=evaluate(self.plan(),quantities={self.first.pk:2,self.second.pk:0})
        scenario=sales_scenario(self.plan(),result,50)
        self.assertEqual(scenario['gross_result']-scenario['cash_difference'],scenario['remaining_stock_value'])

    def test_discount_commission_and_mixed_channel(self):
        self.project.channel='mixed';self.project.save()
        self.product.wholesale_share=50;self.product.discount=10;self.product.commission=10;self.product.sale_cost=1;self.product.save()
        result=evaluate(self.plan(),quantities={self.first.pk:10,self.second.pk:10})
        scenario=sales_scenario(self.plan(),result,100)
        self.assertEqual(scenario['revenue'],Decimal('630.00'))
        self.assertEqual(scenario['selling_costs'],Decimal('83.00'))
        self.assertEqual(scenario['recovered'],Decimal('547.00'))
    def test_snapshot_versions_preserve_costs_and_evidence(self):
        self.first.quantity=20;self.second.quantity=20;self.first.save();self.second.save()
        evidence=Evidence.objects.create(project=self.project,kind='assumption',title='Antes',signal='Supuesto original')
        version=save_version(self.project.pk,self.user,'Original','approved')
        self.product.unit_cost=30;self.product.save();evidence.signal='Modificado';evidence.save()
        version.refresh_from_db()
        self.assertEqual(version.snapshot['result']['variable'],'800.00')
        self.assertEqual(version.snapshot['evidence'][0]['signal'],'Supuesto original')
        self.assertEqual(evaluate(self.plan())['variable'],Decimal('1200.00'))
    def test_cannot_approve_estimated_cost_or_infeasible_plan(self):
        with self.assertRaises(ValidationError):save_version(self.project.pk,self.user,'Vacío','approved')
        self.first.quantity=20;self.second.quantity=20;self.first.save();self.second.save()
        self.product.cost_confirmed=False;self.product.save()
        with self.assertRaises(ValidationError):save_version(self.project.pk,self.user,'Estimado','approved')
        self.assertEqual(save_version(self.project.pk,self.user,'Simulación').status,'simulation')
    def test_preview_is_exact_and_does_not_save(self):
        data=self.quantities_payload(**{'variants-0-quantity':'20','variants-1-quantity':'20'})
        response=self.client.post(reverse('planner:preview',args=[self.project.pk]),data)
        self.assertEqual(response.json()['required'],'1000.00')
        self.assertEqual(response.json()['variable'],'800.00')
        self.first.refresh_from_db();self.assertEqual(self.first.quantity,0)
        self.assertRedirects(self.client.post(reverse('planner:quantities',args=[self.project.pk]),data),reverse('planner:detail',args=[self.project.pk])+'#variantes')
        self.first.refresh_from_db();self.assertEqual(self.first.quantity,20)
    def test_larger_variant_form_is_not_rejected_by_default_http_field_limit(self):
        Variant.objects.bulk_create([Variant(product=self.product,color='Color '+str(i),size='Única') for i in range(250)])
        response=self.client.post(reverse('planner:preview',args=[self.project.pk]),self.quantities_payload())
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.json()['valid'])

    def test_formset_rejects_foreign_missing_duplicate_negative_fractional_ids(self):
        other=Project.objects.create(name='Otro',launch_date=self.project.launch_date,sell_by=self.project.sell_by,budget=100)
        p=Product.objects.create(project=other,name='Otro');v=Variant.objects.create(product=p,color='Rojo',size='Única')
        query=Variant.objects.filter(product__project=self.project)
        for updates in [{'variants-0-id':str(v.pk)},{'variants-1-id':str(self.first.pk)},{'variants-TOTAL_FORMS':'1'},{'variants-0-quantity':'-1'},{'variants-0-quantity':'1.5'}]:
            self.assertFalse(QuantityFormSet(self.quantities_payload(**updates),queryset=query,prefix='variants').is_valid(),updates)
    def test_templates_exports_versions_and_auth(self):
        self.client.post(reverse('planner:generate',args=[self.project.pk]))
        self.assertEqual(PlanVersion.objects.count(),3)
        version=PlanVersion.objects.get(name='Equilibrado')
        for url in [reverse('planner:index'),reverse('planner:detail',args=[self.project.pk]),reverse('planner:version',args=[self.project.pk,version.pk]),reverse('planner:product_edit',args=[self.project.pk,self.product.pk]),reverse('planner:evidence_create',args=[self.project.pk])]:
            self.assertEqual(self.client.get(url).status_code,200,url)
        for entity in ('plan','evidencia','supuestos'):
            response=self.client.get(reverse('planner:export',args=[self.project.pk,version.pk,entity]))
            self.assertEqual(response.status_code,200)
        exported=self.client.get(reverse('planner:export',args=[self.project.pk,version.pk,'plan'])).content.decode('utf-8-sig')
        rows=list(csv.reader(io.StringIO(exported)))
        self.assertEqual(sum(int(r[8]) for r in rows[1:] if r[0]=='Equilibrado'),40)
        self.client.force_login(self.operator)
        self.assertEqual(self.client.get(reverse('planner:detail',args=[self.project.pk])).status_code,200)
        for name in ('generate','save','research','quantities','preview'):
            self.assertEqual(self.client.post(reverse('planner:'+name,args=[self.project.pk]),{}).status_code,403)
        self.client.logout();self.assertEqual(self.client.get(reverse('planner:index')).status_code,302)
    def test_csv_keeps_negative_money_numeric_and_escapes_product_formulas(self):
        self.first.quantity=50;self.first.save()
        self.product.name='=HYPERLINK("unsafe")';self.product.save()
        version=save_version(self.project.pk,self.user,'Simulación inviable')
        response=self.client.get(reverse('planner:export',args=[self.project.pk,version.pk,'plan']))
        rows=list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))
        self.assertEqual(next(row for row in rows if row[0]=='remaining')[3],'-200.00')
        self.assertTrue(rows[1][3].startswith("'=HYPERLINK"))

    def test_apply_version_refuses_changed_structure_and_locked_conflicts(self):
        self.client.post(reverse('planner:generate',args=[self.project.pk]))
        version=PlanVersion.objects.get(name='Equilibrado')
        self.first.locked=True;self.first.save()
        self.client.post(reverse('planner:apply',args=[self.project.pk,version.pk]))
        self.first.refresh_from_db();self.assertEqual(self.first.quantity,0)
        self.first.locked=False;self.first.save()
        self.client.post(reverse('planner:apply',args=[self.project.pk,version.pk]))
        self.first.refresh_from_db();self.assertEqual(self.first.quantity,20)
        Variant.objects.create(product=self.product,color='Marfil',size='M')
        self.first.quantity=0;self.first.save()
        self.client.post(reverse('planner:apply',args=[self.project.pk,version.pk]))
        self.first.refresh_from_db();self.assertEqual(self.first.quantity,0)
    def test_evidence_validation_rejects_dates_availability_and_wrong_variant(self):
        today=timezone.localdate()
        data={'kind':'sales','title':'Prueba','units':'10','period_start':str(today-timedelta(days=2)),'period_end':str(today),'days_in_stock':'5','consulted_date':str(today),'source_type':'own','signal':'Ventas','product':self.product.pk,'variant':self.first.pk}
        self.assertFalse(EvidenceForm(data,project=self.project).is_valid())
        data['days_in_stock']='3';self.assertTrue(EvidenceForm(data,project=self.project).is_valid())
        data['source_type']='local';self.assertFalse(EvidenceForm(data,project=self.project).is_valid())
    def test_variant_duplicate_has_friendly_validation(self):
        form=VariantForm({'color':'Negro','size':'M','stock':0,'quantity':0,'available':'on'},instance=Variant(product=self.product))
        self.assertFalse(form.is_valid());self.assertIn('size',form.errors)
    @override_settings(MARYRUSS_RESEARCH_API_KEY='')
    def test_missing_research_connection_preserves_budget_and_does_not_invent_results(self):
        with self.assertRaises(ValidationError):run_research(self.plan())
        self.assertEqual(self.project.research_runs.count(),0)
        self.assertContains(self.client.get(reverse('planner:detail',args=[self.project.pk])),'Sin investigación actual online')
    def test_manual_report_deduplicates_campaign_and_marks_unknown_dates(self):
        for name,url in [('Primera','https://example.com/ropa?utm_source=a'),('Repetida','https://example.com/ropa?utm_source=b')]:
            Evidence.objects.create(project=self.project,kind='external',title=name,url=url,signal='Observación',source_type='local')
        report=evidence_report(self.plan())
        self.assertEqual(report['sample_size'],1);self.assertEqual(report['duplicates'],1);self.assertEqual(report['unknown_dates'],1)
        self.assertEqual(canonical_url('https://example.com/item?id=12&utm_source=a'),'https://example.com/item?id=12')
    @override_settings(MARYRUSS_RESEARCH_API_KEY='test-placeholder-not-real')
    @patch('planner.research.urlopen')
    def test_research_provider_contract_cache_and_no_untrusted_html_execution(self,opened):
        opened.return_value.__enter__.return_value.read.return_value=json.dumps({'results':[{'url':'https://example.com/ropa?utm_source=a','title':'Colección','content':'Texto de fuente <script>no ejecutar</script>'},{'url':'https://example.com/ropa?utm_source=b','title':'Duplicada'}]}).encode()
        run,cached=run_research(self.plan())
        self.assertFalse(cached);self.assertEqual(run.report['sample_size'],1)
        self.assertIsNone(run.report['sources'][0]['published_date'])
        again,cached=run_research(self.plan());self.assertTrue(cached);self.assertEqual(again.pk,run.pk);self.assertEqual(opened.call_count,1)
        self.assertContains(self.client.get(reverse('planner:detail',args=[self.project.pk])),'&lt;script&gt;')
        opened.side_effect=URLError('offline')
        with self.assertRaises(ValidationError):run_research(self.plan(),force=True)
        self.assertEqual(self.project.research_runs.count(),1)
