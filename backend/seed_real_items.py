import asyncio
from datetime import datetime, timezone
from app.database.mongodb import mongodb_manager

REAL_PRODUCTS = [
    {
        'code': 'FP-ENV-100',
        'name': 'Automatic Envelope Making Machine ENV-100',
        'description': 'Compact envelope folding and gluing machine for pocket & wallet envelopes (up to 12,000 pcs/hr)',
        'category_id': 'CAT-PRESS',
        'uom': 'SET',
        'drawing_no': 'DWG-ENV-100-01',
        'revision_no': 'R2',
        'standard_cost': 185000.0,
        'selling_price': 245000.0,
        'min_stock_level': 1,
        'unit_id': 'BOTH',
        'is_active': True,
    },
    {
        'code': 'FP-ENV-200',
        'name': 'High-Speed Commercial Envelope Making Machine ENV-200',
        'description': 'Heavy-duty industrial envelope machine with auto vacuum feeder and silicone peel & seal unit (up to 22,000 pcs/hr)',
        'category_id': 'CAT-PRESS',
        'uom': 'SET',
        'drawing_no': 'DWG-ENV-200-01',
        'revision_no': 'R3',
        'standard_cost': 310000.0,
        'selling_price': 415000.0,
        'min_stock_level': 1,
        'unit_id': 'BOTH',
        'is_active': True,
    },
    {
        'code': 'FP-PKG-300',
        'name': 'Corrugated Carton Automatic Packing Machine PKG-300',
        'description': 'Automated box erector, side-belt taping and strapping workstation with pneumatic flattener',
        'category_id': 'CAT-PRESS',
        'uom': 'SET',
        'drawing_no': 'DWG-PKG-300-01',
        'revision_no': 'R1',
        'standard_cost': 420000.0,
        'selling_price': 565000.0,
        'min_stock_level': 1,
        'unit_id': 'BOTH',
        'is_active': True,
    },
    {
        'code': 'FP-ENV-MINI',
        'name': 'Semi-Automatic Tabletop Envelope Machine ENV-MINI',
        'description': 'Entry-level compact envelope folder for small stationery print shops (up to 4,500 pcs/hr)',
        'category_id': 'CAT-PRESS',
        'uom': 'SET',
        'drawing_no': 'DWG-ENV-M-01',
        'revision_no': 'R0',
        'standard_cost': 95000.0,
        'selling_price': 128000.0,
        'min_stock_level': 2,
        'unit_id': 'BOTH',
        'is_active': True,
    },
    {
        'code': 'FP-DIE-PUNCH-40',
        'name': 'Heavy Duty Hydraulic Die Punching Machine DP-40',
        'description': '40-Ton hydraulic beam die cutting and blanking press for window envelopes and cartons',
        'category_id': 'CAT-PRESS',
        'uom': 'SET',
        'drawing_no': 'DWG-DP40-01',
        'revision_no': 'R1',
        'standard_cost': 240000.0,
        'selling_price': 325000.0,
        'min_stock_level': 1,
        'unit_id': 'Unit_1',
        'is_active': True,
    },
    {
        'code': 'FP-PAPER-FOLD-120',
        'name': 'High-Precision Commercial Paper Folder PF-120',
        'description': '4-buckle continuous paper folder with scoring and micro-perforation wheel attachments',
        'category_id': 'CAT-PRESS',
        'uom': 'SET',
        'drawing_no': 'DWG-PF120-02',
        'revision_no': 'R2',
        'standard_cost': 215000.0,
        'selling_price': 295000.0,
        'min_stock_level': 1,
        'unit_id': 'Unit_2',
        'is_active': True,
    },
    {
        'code': 'FP-GLUE-APPL-10',
        'name': 'Precision Hot-Melt Adhesive Applicator GA-10',
        'description': 'Dual-nozzle heated adhesive pumping system with PLC temperature control and timer',
        'category_id': 'CAT-PRESS',
        'uom': 'SET',
        'drawing_no': 'DWG-GA10-01',
        'revision_no': 'R1',
        'standard_cost': 62000.0,
        'selling_price': 85000.0,
        'min_stock_level': 3,
        'unit_id': 'BOTH',
        'is_active': True,
    },
    {
        'code': 'FP-SPARE-FEEDER-VAC',
        'name': 'Top Suction Vacuum Feeder Assembly Module',
        'description': 'Replacement high-speed bottom suction vacuum sheet feeder for ENV series machines',
        'category_id': 'CAT-PRESS',
        'uom': 'NOS',
        'drawing_no': 'DWG-SF-01',
        'revision_no': 'R1',
        'standard_cost': 48000.0,
        'selling_price': 65000.0,
        'min_stock_level': 4,
        'unit_id': 'Unit_2',
        'is_active': True,
    },
    {
        'code': 'FP-SPARE-ROLLER-CR',
        'name': 'Hard Chrome Plated Steel Pressure Roller Set',
        'description': 'Ground & polished steel folding roller set with high wear resistance (Pair of 2)',
        'category_id': 'CAT-PRESS',
        'uom': 'SET',
        'drawing_no': 'DWG-RL-04',
        'revision_no': 'R1',
        'standard_cost': 19500.0,
        'selling_price': 28000.0,
        'min_stock_level': 5,
        'unit_id': 'Unit_1',
        'is_active': True,
    },
    {
        'code': 'FP-TOOL-DIE-A4',
        'name': 'Custom Hardened Steel Envelope Cutting Die Set (C5/A4)',
        'description': 'Heat-treated D2 steel blanking die for standard business correspondence envelopes',
        'category_id': 'CAT-PRESS',
        'uom': 'SET',
        'drawing_no': 'DWG-DIE-C5',
        'revision_no': 'R1',
        'standard_cost': 31000.0,
        'selling_price': 42000.0,
        'min_stock_level': 2,
        'unit_id': 'Unit_1',
        'is_active': True,
    }
]

REAL_MATERIALS = [
    {'code': 'RM-MS-PLATE-6MM', 'name': 'Mild Steel Plate 6mm IS 2062', 'standard_cost': 65.0, 'uom': 'KG', 'hsn_code': '72085100', 'category_id': 'CAT-STEEL', 'description': 'Hot rolled steel plate 6mm for machine base fabrication'},
    {'code': 'RM-MS-PLATE-10MM', 'name': 'Mild Steel Plate 10mm IS 2062', 'standard_cost': 68.0, 'uom': 'KG', 'hsn_code': '72085100', 'category_id': 'CAT-STEEL', 'description': 'Heavy structural steel plate 10mm for side frames'},
    {'code': 'RM-SS-ROD-20MM', 'name': 'Stainless Steel Round Bar 20mm SS304', 'standard_cost': 240.0, 'uom': 'KG', 'hsn_code': '72221100', 'category_id': 'CAT-STEEL', 'description': 'Precision ground SS304 shafting for roller drive'},
    {'code': 'RM-CI-CAST-001', 'name': 'Cast Iron Main Gearbox Housing Body', 'standard_cost': 35000.0, 'uom': 'PCS', 'hsn_code': '84834000', 'category_id': 'CAT-CASTING', 'description': 'Grade 25 CI casting rough machined for main drive'},
    {'code': 'RM-MS-CHANNEL', 'name': 'MS Structural Channel 100x50 mm', 'standard_cost': 72.0, 'uom': 'KG', 'hsn_code': '72163100', 'category_id': 'CAT-STEEL', 'description': 'ISMC 100 steel channel for bed frame'},
    {'code': 'RM-MOTOR-0.5HP', 'name': 'AC Induction Motor 0.5 HP 3-Phase 1440 RPM', 'standard_cost': 4500.0, 'uom': 'PCS', 'hsn_code': '85015100', 'category_id': 'CAT-ELECTRICAL', 'description': 'Foot mounted TEFC motor with B5 flange for feed unit'},
    {'code': 'RM-MOTOR-1HP', 'name': 'AC Induction Motor 1.0 HP 3-Phase 1440 RPM', 'standard_cost': 7800.0, 'uom': 'PCS', 'hsn_code': '85015100', 'category_id': 'CAT-ELECTRICAL', 'description': 'IE3 premium efficiency motor for main spindle drive'},
    {'code': 'RM-BEARING-6205', 'name': 'Deep Groove Ball Bearing 6205-2RS SKF', 'standard_cost': 350.0, 'uom': 'PCS', 'hsn_code': '84821011', 'category_id': 'CAT-BEARINGS', 'description': 'Rubber sealed high-speed ball bearing for rollers'},
    {'code': 'RM-CAPACITOR-25', 'name': 'Motor Run Capacitor 25 MFD 440V', 'standard_cost': 180.0, 'uom': 'PCS', 'hsn_code': '85322500', 'category_id': 'CAT-ELECTRICAL', 'description': 'Heavy duty polypropylene film capacitor'},
    {'code': 'RM-RUBBER-GSKT', 'name': 'Nitrile Rubber Sealing Gasket Strip 3mm', 'standard_cost': 120.0, 'uom': 'MTR', 'hsn_code': '40169320', 'category_id': 'CAT-HARDWARE', 'description': 'Oil and heat resistant 70 Shore A rubber gasket'},
    {'code': 'RM-NYLON-BUSH', 'name': 'Nylon 6 Self-Lubricating Bush 20mm ID', 'standard_cost': 85.0, 'uom': 'PCS', 'hsn_code': '39269099', 'category_id': 'CAT-HARDWARE', 'description': 'Precision machined nylon sleeve bush for guide pins'},
    {'code': 'RM-WELD-ROD-E6013', 'name': 'Mild Steel Welding Electrode E6013 3.15mm', 'standard_cost': 320.0, 'uom': 'PKT', 'hsn_code': '83111000', 'category_id': 'CAT-CONSUMABLE', 'description': '5 kg box rutile coated manual metal arc welding rods'},
    {'code': 'RM-CUTTING-OIL', 'name': 'Water Soluble Cutting & CNC Coolant Oil', 'standard_cost': 220.0, 'uom': 'LTR', 'hsn_code': '27101980', 'category_id': 'CAT-CONSUMABLE', 'description': 'Heavy duty biostable cutting emulsion for machining'},
    {'code': 'RM-PAINT-GREY', 'name': 'Industrial Epoxy Machine Grey Paint', 'standard_cost': 380.0, 'uom': 'LTR', 'hsn_code': '32082090', 'category_id': 'CAT-CONSUMABLE', 'description': 'RAL 7035 machine tool enamel coating with hardener'},
    {'code': 'RM-PNEU-CYL-32', 'name': 'Double Acting Pneumatic Air Cylinder 32x100mm', 'standard_cost': 1850.0, 'uom': 'PCS', 'hsn_code': '84123100', 'category_id': 'CAT-PNEUMATICS', 'description': 'Pneumatic cylinder for folding arms mechanism'},
    {'code': 'RM-TIMING-BELT', 'name': 'Rubber Timing Belt 8M Pitch 30mm Wide', 'standard_cost': 750.0, 'uom': 'PCS', 'hsn_code': '40103500', 'category_id': 'CAT-HARDWARE', 'description': 'High torque drive synchronous belt with fiberglass cords'},
    {'code': 'RM-SENSOR-PROX', 'name': 'Inductive Proximity Sensor M12 NPN NO', 'standard_cost': 620.0, 'uom': 'PCS', 'hsn_code': '85365090', 'category_id': 'CAT-ELECTRICAL', 'description': 'Flush mount 4mm sensing distance position sensor for cam indexing'}
]

async def seed():
    await mongodb_manager.connect()
    db = mongodb_manager.get_database()
    now = datetime.now(timezone.utc)
    
    # Upsert Finished Products
    for p in REAL_PRODUCTS:
        p_data = {**p, 'updated_at': now}
        await db['finished_products'].update_one(
            {'code': p['code']},
            {'$set': p_data, '$setOnInsert': {'created_at': now, 'created_by': 'admin@rgtech.com'}},
            upsert=True
        )

    # Upsert Raw Materials
    for m in REAL_MATERIALS:
        m_data = {
            **m,
            'unit_id': 'BOTH',
            'is_active': True,
            'reorder_level': 100.0,
            'safety_stock': 50.0,
            'updated_at': now
        }
        await db['raw_materials'].update_one(
            {'code': m['code']},
            {'$set': m_data, '$setOnInsert': {'created_at': now, 'created_by': 'admin@rgtech.com'}},
            upsert=True
        )

    p_count = await db['finished_products'].count_documents({})
    m_count = await db['raw_materials'].count_documents({})
    print(f'SUCCESS! Seeded {p_count} finished products and {m_count} raw materials.')
    await mongodb_manager.disconnect()

if __name__ == '__main__':
    asyncio.run(seed())
