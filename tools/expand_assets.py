"""Add test definitions for otherwise unused equipment assets and crafting pieces."""
from pathlib import Path
import copy, json, re
import xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'module'/'CIItemLab'/'ModuleData'
SOURCE=Path(r'C:\Program Files (x86)\Steam\steamapps\workshop\content\261550\3245522442\ModuleData')
index=json.loads((ROOT/'docs'/'asset-mesh-index.json').read_text())
catalog=json.loads((ROOT/'docs'/'item-catalog.json').read_text(encoding='utf-8'))
trees=[E.parse(f) for f in (DATA/'labitems').glob('*.xml') if f.name!='zz_asset_tests.xml']
items=[e for t in trees for e in t.getroot()]
used={e.get('mesh') for t in trees for e in t.getroot().iter() if e.get('mesh')}
pieces=E.parse(DATA/'lab_crafting_pieces.xml')
used|={e.get('mesh') for e in pieces.getroot()}
used|={e.get('mesh') for f in SOURCE.rglob('*.xml') for e in E.parse(f).getroot().iter() if e.get('mesh')}
extra=E.Element('Items'); skipped=[]
def classify(name):
 n=name.lower()
 if any(x in n for x in ['horse_armor','camel_armor','horse_barding']): return 'HorseHarness'
 if any(x in n for x in ['glove','gauntlet']): return 'HandArmor'
 if any(x in n for x in ['boot','greave','hose','_legs','sabat']): return 'LegArmor'
 if any(x in n for x in ['pauldron','spaulder','shoulder','cloak','cape','scarf']): return 'Cape'
 if any(x in n for x in ['helmet','helm','bascinet','barbute','sallet','skullcap','kettle','coif','_hood','_cap','casco']): return 'HeadArmor'
 if any(x in n for x in ['armor','armour','cuirass','gambeson','surcoat','tabard','tabbard','brigandine','coat','jupon','waffenrock','garment','breastplate','broigne','kastenbrust','lamellar','robe','mail']): return 'BodyArmor'
 if any(x in n for x in ['shield','escudo']): return 'Shield'
 if any(x in n for x in ['poleaxe','polehammer','halberd','glaive','spear','lance','pike']): return 'Polearm'
 if any(x in n for x in ['sword','sabre','saber','falchion','rapier','dagger','axe','mace','hammer']): return 'OneHandedWeapon'
 return None
categories={'HeadArmor':'Helmet','HandArmor':'Gloves','LegArmor':'Boots','Cape':'Shoulders','BodyArmor':'Armor','HorseHarness':'Harness','Shield':'Shield','Polearm':'Polearm','OneHandedWeapon':'Weapon'}
def add_record(item,mesh,pack,kind):
 extra.append(item)
 catalog.append({'id':item.get('id'),'original_id':item.get('id')[6:],'name':item.get('name'),
                 'category':categories.get(item.get('Type'),'Weapon'),'pack':pack,'mesh':mesh,
                 'type':item.get('Type', 'CraftedWeapon'),'file':'zz_asset_tests.xml','definition_kind':kind})

for asset in index:
 mesh=asset['name']; low=mesh.lower(); typ=classify(mesh)
 if mesh == 'bre_kettlehelm_2':
  skipped.append({'mesh':mesh,'reason':'quarantined: reported native crash when equipped'}); continue
 if mesh in used: continue
 if any(x in low for x in ['clothsim','simulation','_clo','clo_','_rein','_holster','scabbard','sheath']) or low.endswith(('_slim','_female','_male','_converted','_converted_slim')):
  skipped.append({'mesh':mesh,'reason':'auxiliary cloth, gender variant or attachment'}); continue
 if not typ or not asset['parts']:
  skipped.append({'mesh':mesh,'reason':'not identified as complete equipment'}); continue
 if typ in ['HeadArmor','BodyArmor','HandArmor','LegArmor','Cape','HorseHarness'] and not any(p.get('skin',0)>0 for p in asset['parts']):
  skipped.append({'mesh':mesh,'reason':'no skeletal skin data: not safe for generated wearable equipment'}); continue
 if typ in ['Polearm','OneHandedWeapon'] and any(x in low for x in ['_blade','_head','_shaft','_handle','_guard','_pommel','_grip']):
  skipped.append({'mesh':mesh,'reason':'weapon component without equipment definition'}); continue
 # Clone a compatible item definition; mesh names alone do not contain gameplay stats.
 candidates=[e for e in items if e.tag=='Item' and e.get('Type')==typ]
 if typ=='Polearm':
  # Use a native polearm template when CI's polearms are all crafted.
  modules=Path(r'C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord\Modules')
  candidates=[]
  for m in ['Native','SandBoxCore','Multiplayer']:
   for f in (modules/m/'ModuleData').rglob('*items*.xml'):
    try: native_tree=E.parse(f)
    except E.ParseError: continue
    candidates.extend(e for e in native_tree.getroot() if e.tag=='Item' and e.get('Type')==typ)
 if not candidates:
  skipped.append({'mesh':mesh,'reason':'no safe compatible equipment template'}); continue
 original=max(candidates,key=lambda e:len(__import__('os').path.commonprefix([e.get('mesh',''),mesh])))
 item=copy.deepcopy(original); item.set('mesh',mesh)
 for k in ['holster_mesh','holster_mesh_with_weapon','skeleton_name','body_name','holster_body_name']:
  item.attrib.pop(k,None)
 if typ in ['Polearm','OneHandedWeapon']: item.set('body_name','bo_sword_one_handed')
 id='asset_'+re.sub(r'[^\w.-]','_',mesh); item.set('id','cilab_'+id)
 pack=asset['package'].removesuffix('.tpac')
 item.set('name',f'[{categories[typ]} | {pack} | Asset Test] {mesh} [{id}]')
 item.set('is_merchandise','false'); item.set('value','1'); item.set('difficulty','0')
 for n in item.iter():
  if 'difficulty' in n.attrib: n.set('difficulty','0')
 add_record(item,mesh,pack,'asset_test'); used.add(mesh)

# Create representative assembled weapons for unused CI crafting pieces, retaining
# a known working recipe and swapping a compatible component from its own template.
templates=E.parse(DATA/'lab_crafting_templates.xml').getroot()
descriptions=E.parse(DATA/'lab_weapon_descriptions.xml').getroot()
native_data=Path(r'C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord\Modules\Native\ModuleData')
native_templates={e.get('id'):e for e in E.parse(native_data/'crafting_templates.xml').getroot()}
native_descriptions={e.get('id'):e for e in E.parse(native_data/'weapon_descriptions.xml').getroot()}
native_pieces={e.get('id'):e for e in E.parse(native_data/'crafting_pieces.xml').getroot()}
native_recipes=[]
for f in Path(r'C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord\Modules\SandBoxCore\ModuleData').rglob('*.xml'):
 try: tree=E.parse(f)
 except E.ParseError: continue
 native_recipes.extend(e for e in tree.getroot() if e.tag=='CraftedItem')

# Build isolated generic test templates, preserving valid native crafting behavior.
test_templates={}
for kind in ['TwoHandedSword','OneHandedSword','TwoHandedPolearm','OneHandedAxe','Mace']:
 original=native_templates.get(kind)
 sample=next((r for r in native_recipes if r.get('crafting_template')==kind),None)
 if original is None or sample is None: continue
 t=copy.deepcopy(original); tid='cilab_asset_template_'+kind; t.set('id',tid)
 mapping={}
 for ref in t.findall('./WeaponDescriptions/WeaponDescription'):
  old=ref.get('id'); desc=native_descriptions.get(old)
  if desc is None: continue
  did='cilab_asset_desc_'+kind+'_'+old; mapping[old]=did; ref.set('id',did)
  d=copy.deepcopy(desc); d.set('id',did); descriptions.append(d)
 for stats in t.findall('StatsData'):
  if stats.get('weapon_description') in mapping: stats.set('weapon_description',mapping[stats.get('weapon_description')])
 templates.append(t); test_templates[kind]=(t,copy.deepcopy(sample))

# Raw sword/axe/polearm parts without XML definitions get clearly labeled
# synthetic crafting pieces, cloned from a matching native recipe component.
defined_meshes={e.get('mesh') for e in pieces.getroot()}
for asset in index:
 mesh=asset['name']; n=mesh.lower()
 if mesh in used or mesh in defined_meshes: continue
 slot=next((typ for term,typ in [('blade','Blade'),('head','Blade'),('guard','Guard'),('pommel','Pommel'),('grip','Handle'),('handle','Handle'),('shaft','Handle')] if re.search(r'(^|_)'+term+r'(_|$)',n)),None)
 if not slot or not any(x in n for x in ['sword','zweihander','claymore','braveheart','flamberg','uhtred','kevfz','axe','hammer','lance']): continue
 kind='TwoHandedPolearm' if any(x in n for x in ['pole','hammer','lance']) else 'OneHandedAxe' if 'axe' in n else 'TwoHandedSword'
 pair=test_templates.get(kind)
 if pair is None: continue
 base_ref=next((p.get('id') for r in native_recipes if r.get('crafting_template')==kind for p in r.findall('./Pieces/Piece') if p.get('Type')==slot),None)
 if base_ref is None: base_ref=next((p.get('id') for p in native_pieces.values() if p.get('piece_type')==slot),None)
 original=native_pieces.get(base_ref)
 if original is None: continue
 piece=copy.deepcopy(original); piece.set('id','cilab_asset_piece_'+re.sub(r'[^\w.-]','_',mesh)); piece.set('mesh',mesh)
 piece.set('name','Asset Test '+mesh); pieces.getroot().append(piece); defined_meshes.add(mesh)

template_pieces={t.get('id'):{e.get('piece_id') for e in t.findall('./UsablePieces/UsablePiece')} for t in templates}
recipes=[e for e in items if e.tag=='CraftedItem']
used_pieces={p.get('id') for e in recipes for p in e.findall('./Pieces/Piece')}
for piece in pieces.getroot():
 pid=piece.get('id'); mesh=piece.get('mesh','')
 if not pid.startswith('cilab_') or pid in used_pieces or not mesh: continue
 # Only pieces bundled in CI's packages, rather than imported native MP pieces.
 if mesh not in {a['name'] for a in index}: continue
 piece_type=piece.get('piece_type')
 compatible=[r for r in recipes if pid in template_pieces.get(r.get('crafting_template'),set())
             and any(p.get('Type')==piece_type for p in r.findall('./Pieces/Piece'))]
 if not compatible:
  kind='TwoHandedPolearm' if any(x in mesh.lower() for x in ['lance','spear','pole','hammer']) else 'OneHandedAxe' if 'axe' in mesh.lower() else 'TwoHandedSword'
  pair=test_templates.get(kind)
  if pair is not None:
   t,base_recipe=pair
   base_recipe=next((r for r in native_recipes if r.get('crafting_template')==kind and any(p.get('Type')==piece_type for p in r.findall('./Pieces/Piece'))),base_recipe)
   recipe=copy.deepcopy(base_recipe); recipe.set('crafting_template',t.get('id'))
   if not any(p.get('Type')==piece_type for p in recipe.findall('./Pieces/Piece')):
    if not any(p.get('piece_type')==piece_type for p in t.findall('./PieceDatas/PieceData')):
     skipped.append({'mesh':mesh,'reason':'component slot unsupported by native test template'}); continue
    E.SubElement(recipe.find('Pieces'),'Piece',id=pid,Type=piece_type)
   usable=t.find('UsablePieces')
   if usable is None: usable=E.SubElement(t,'UsablePieces')
   E.SubElement(usable,'UsablePiece',piece_id=pid)
   for ref in t.findall('./WeaponDescriptions/WeaponDescription'):
    desc=next((d for d in descriptions if d.get('id')==ref.get('id')),None)
    if desc is not None:
     available=desc.find('AvailablePieces')
     if available is None: available=E.SubElement(desc,'AvailablePieces')
     E.SubElement(available,'AvailablePiece',id=pid)
   compatible=[recipe]
  else:
   skipped.append({'mesh':mesh,'reason':'crafting piece has no compatible complete CI recipe'}); continue
 recipe=copy.deepcopy(compatible[0])
 slot=next(p for p in recipe.findall('./Pieces/Piece') if p.get('Type')==piece_type)
 slot.set('id',pid); slot.attrib.pop('scale_factor',None)
 id='piece_test_'+pid[6:]; recipe.set('id','cilab_'+id)
 recipe.set('name',f'[Weapon | Crafting | Asset Test] {mesh} [{id}]')
 add_record(recipe,mesh,'Crafting','component_test')

E.indent(extra); E.ElementTree(extra).write(DATA/'labitems'/'zz_asset_tests.xml',encoding='utf-8',xml_declaration=True)
known_pieces=set(native_pieces)|{p.get('id') for p in pieces.getroot()}
for root in [templates, descriptions]:
 for parent in root.iter():
  for e in list(parent):
   key='piece_id' if e.tag=='UsablePiece' else 'id' if e.tag=='AvailablePiece' else None
   if key and e.get(key) not in known_pieces:
    if 'cilab_'+e.get(key,'') in known_pieces: e.set(key,'cilab_'+e.get(key))
    else: parent.remove(e)
for tree,path in [(pieces,DATA/'lab_crafting_pieces.xml'),(E.ElementTree(templates),DATA/'lab_crafting_templates.xml'),(E.ElementTree(descriptions),DATA/'lab_weapon_descriptions.xml')]:
 E.indent(tree); tree.write(path,encoding='utf-8',xml_declaration=True)
(ROOT/'docs'/'item-catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False),encoding='utf-8')
covered={e.get('mesh') for e in catalog if e.get('mesh')}
skipped=[s for s in skipped if s['mesh'] not in covered]
report={'additional_test_items':len(extra),'total_items':len(catalog),'unconverted_assets':skipped}
(ROOT/'docs'/'asset-expansion-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('Added',len(extra),'asset/component test items; total',len(catalog),'; unconverted records',len(skipped))
