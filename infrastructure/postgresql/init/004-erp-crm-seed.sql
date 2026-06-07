INSERT INTO crm_accounts (account_code, name, segment, status, annual_revenue)
VALUES ('CRM-SEED-ACME', 'Acme Industrial', 'enterprise', 'active', 1250000.00),
       ('CRM-SEED-NOVA', 'Nova Retail', 'mid-market', 'active', 480000.00)
ON CONFLICT (account_code) DO UPDATE
SET name = EXCLUDED.name,
    segment = EXCLUDED.segment,
    status = EXCLUDED.status,
    annual_revenue = EXCLUDED.annual_revenue;

INSERT INTO crm_contacts (account_id, contact_code, email, full_name, role_title, lifecycle_stage)
VALUES ((SELECT id FROM crm_accounts WHERE account_code = 'CRM-SEED-ACME'), 'CRM-SEED-CONTACT-ACME-1',
        'ana.acme@example.com', 'Ana Acme', 'Operations Director', 'customer'),
       ((SELECT id FROM crm_accounts WHERE account_code = 'CRM-SEED-NOVA'), 'CRM-SEED-CONTACT-NOVA-1',
        'nora.nova@example.com', 'Nora Nova', 'Finance Manager', 'prospect')
ON CONFLICT (contact_code) DO UPDATE
SET account_id = EXCLUDED.account_id,
    email = EXCLUDED.email,
    full_name = EXCLUDED.full_name,
    role_title = EXCLUDED.role_title,
    lifecycle_stage = EXCLUDED.lifecycle_stage;

INSERT INTO crm_opportunities (account_id, opportunity_code, title, stage, expected_amount)
VALUES ((SELECT id FROM crm_accounts WHERE account_code = 'CRM-SEED-ACME'), 'CRM-SEED-OPP-ACME-ERP',
        'ERP rollout', 'proposal', 92000.00),
       ((SELECT id FROM crm_accounts WHERE account_code = 'CRM-SEED-NOVA'), 'CRM-SEED-OPP-NOVA-CRM',
        'CRM expansion', 'qualified', 36000.00)
ON CONFLICT (opportunity_code) DO UPDATE
SET account_id = EXCLUDED.account_id,
    title = EXCLUDED.title,
    stage = EXCLUDED.stage,
    expected_amount = EXCLUDED.expected_amount;

INSERT INTO crm_activities (account_id, contact_id, activity_code, activity_type, subject, status)
VALUES ((SELECT id FROM crm_accounts WHERE account_code = 'CRM-SEED-ACME'),
        (SELECT id FROM crm_contacts WHERE contact_code = 'CRM-SEED-CONTACT-ACME-1'),
        'CRM-SEED-ACT-ACME-CALL', 'call', 'Quarterly review', 'completed'),
       ((SELECT id FROM crm_accounts WHERE account_code = 'CRM-SEED-NOVA'),
        (SELECT id FROM crm_contacts WHERE contact_code = 'CRM-SEED-CONTACT-NOVA-1'),
        'CRM-SEED-ACT-NOVA-DEMO', 'demo', 'Product demo', 'scheduled')
ON CONFLICT (activity_code) DO UPDATE
SET account_id = EXCLUDED.account_id,
    contact_id = EXCLUDED.contact_id,
    activity_type = EXCLUDED.activity_type,
    subject = EXCLUDED.subject,
    status = EXCLUDED.status;

INSERT INTO ops_suppliers (supplier_code, name, status, rating_score)
VALUES ('OPS-SEED-SUP-ATLANTIC', 'Atlantic Supplies', 'active', 8.70),
       ('OPS-SEED-SUP-IBERIA', 'Iberia Components', 'active', 9.10)
ON CONFLICT (supplier_code) DO UPDATE
SET name = EXCLUDED.name,
    status = EXCLUDED.status,
    rating_score = EXCLUDED.rating_score;

INSERT INTO ops_products (supplier_id, sku, name, category, unit_cost, status)
VALUES ((SELECT id FROM ops_suppliers WHERE supplier_code = 'OPS-SEED-SUP-ATLANTIC'), 'OPS-SEED-SKU-LAPTOP',
        'Professional laptop', 'hardware', 820.00, 'active'),
       ((SELECT id FROM ops_suppliers WHERE supplier_code = 'OPS-SEED-SUP-IBERIA'), 'OPS-SEED-SKU-DOCK',
        'USB-C dock', 'hardware', 115.00, 'active')
ON CONFLICT (sku) DO UPDATE
SET supplier_id = EXCLUDED.supplier_id,
    name = EXCLUDED.name,
    category = EXCLUDED.category,
    unit_cost = EXCLUDED.unit_cost,
    status = EXCLUDED.status;

INSERT INTO ops_warehouses (warehouse_code, name, region, capacity_units, status)
VALUES ('OPS-SEED-WH-MADRID', 'Madrid Hub', 'center', 12000.00, 'active'),
       ('OPS-SEED-WH-LISBON', 'Lisbon Hub', 'west', 6500.00, 'active')
ON CONFLICT (warehouse_code) DO UPDATE
SET name = EXCLUDED.name,
    region = EXCLUDED.region,
    capacity_units = EXCLUDED.capacity_units,
    status = EXCLUDED.status;

INSERT INTO ops_inventory_movements (product_id, warehouse_id, movement_code, movement_type, quantity, reason)
VALUES ((SELECT id FROM ops_products WHERE sku = 'OPS-SEED-SKU-LAPTOP'),
        (SELECT id FROM ops_warehouses WHERE warehouse_code = 'OPS-SEED-WH-MADRID'),
        'OPS-SEED-MOV-LAPTOP-IN', 'inbound', 25.00, 'initial stock'),
       ((SELECT id FROM ops_products WHERE sku = 'OPS-SEED-SKU-DOCK'),
        (SELECT id FROM ops_warehouses WHERE warehouse_code = 'OPS-SEED-WH-LISBON'),
        'OPS-SEED-MOV-DOCK-IN', 'inbound', 80.00, 'initial stock')
ON CONFLICT (movement_code) DO UPDATE
SET product_id = EXCLUDED.product_id,
    warehouse_id = EXCLUDED.warehouse_id,
    movement_type = EXCLUDED.movement_type,
    quantity = EXCLUDED.quantity,
    reason = EXCLUDED.reason;

INSERT INTO sales_orders (account_id, contact_id, order_number, status, total_amount)
VALUES ((SELECT id FROM crm_accounts WHERE account_code = 'CRM-SEED-ACME'),
        (SELECT id FROM crm_contacts WHERE contact_code = 'CRM-SEED-CONTACT-ACME-1'),
        'SALES-SEED-ORD-ACME-1', 'confirmed', 1870.00),
       ((SELECT id FROM crm_accounts WHERE account_code = 'CRM-SEED-NOVA'),
        (SELECT id FROM crm_contacts WHERE contact_code = 'CRM-SEED-CONTACT-NOVA-1'),
        'SALES-SEED-ORD-NOVA-1', 'draft', 345.00)
ON CONFLICT (order_number) DO UPDATE
SET account_id = EXCLUDED.account_id,
    contact_id = EXCLUDED.contact_id,
    status = EXCLUDED.status,
    total_amount = EXCLUDED.total_amount;

INSERT INTO sales_order_lines (order_id, product_id, line_code, quantity, unit_price, line_status)
VALUES ((SELECT id FROM sales_orders WHERE order_number = 'SALES-SEED-ORD-ACME-1'),
        (SELECT id FROM ops_products WHERE sku = 'OPS-SEED-SKU-LAPTOP'),
        'SALES-SEED-LINE-ACME-LAPTOP', 2.00, 935.00, 'confirmed'),
       ((SELECT id FROM sales_orders WHERE order_number = 'SALES-SEED-ORD-NOVA-1'),
        (SELECT id FROM ops_products WHERE sku = 'OPS-SEED-SKU-DOCK'),
        'SALES-SEED-LINE-NOVA-DOCK', 3.00, 115.00, 'draft')
ON CONFLICT (line_code) DO UPDATE
SET order_id = EXCLUDED.order_id,
    product_id = EXCLUDED.product_id,
    quantity = EXCLUDED.quantity,
    unit_price = EXCLUDED.unit_price,
    line_status = EXCLUDED.line_status;

INSERT INTO sales_invoices (order_id, invoice_number, status, amount_due)
VALUES ((SELECT id FROM sales_orders WHERE order_number = 'SALES-SEED-ORD-ACME-1'), 'SALES-SEED-INV-ACME-1',
        'issued', 1870.00),
       ((SELECT id FROM sales_orders WHERE order_number = 'SALES-SEED-ORD-NOVA-1'), 'SALES-SEED-INV-NOVA-1',
        'draft', 345.00)
ON CONFLICT (invoice_number) DO UPDATE
SET order_id = EXCLUDED.order_id,
    status = EXCLUDED.status,
    amount_due = EXCLUDED.amount_due;

INSERT INTO sales_payments (invoice_id, payment_reference, status, amount_paid)
VALUES ((SELECT id FROM sales_invoices WHERE invoice_number = 'SALES-SEED-INV-ACME-1'), 'SALES-SEED-PAY-ACME-1',
        'captured', 1870.00),
       ((SELECT id FROM sales_invoices WHERE invoice_number = 'SALES-SEED-INV-NOVA-1'), 'SALES-SEED-PAY-NOVA-1',
        'pending', 0.00)
ON CONFLICT (payment_reference) DO UPDATE
SET invoice_id = EXCLUDED.invoice_id,
    status = EXCLUDED.status,
    amount_paid = EXCLUDED.amount_paid;
