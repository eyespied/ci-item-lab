from pathlib import Path
import xml.etree.ElementTree as E
import re
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'module'/'CIItemLab'/'ModuleData'
SRC=Path(r'C:\Program Files (x86)\Steam\steamapps\workshop\content\261550\3245522442\ModuleData')
clans={e.get('id'):e for e in E.parse(SRC/'ci_clans.xml').getroot().iter('Clan')}
uses=defaultdict(set)
for f in (SRC/'ciclasses').glob('*.xml'):
 for c in E.parse(f).getroot().iter('Class'):
  clan=clans.get(c.get('clan'))
  if clan is None: continue
  color=(c.get('color1') or clan.get('color1'),c.get('color2') or clan.get('color2'),c.get('clan'))
  for e in c.iter('equipment'):
   if e.get('id') not in ['null',None]: uses[e.get('id')].add(color)
root=E.Element('ItemColors')
for id,clan in clans.items():
 E.SubElement(root,'Clan',id=id,name=clan.get('name',id),color1=clan.get('color1'),color2=clan.get('color2'))
count=0
for file in (DATA/'labitems').glob('*.xml'):
 tree=E.parse(file); changed=False
 for e in tree.getroot():
  if e.get('Type') not in ['HeadArmor','BodyArmor','Cape','HandArmor','LegArmor','HorseHarness']: continue
  original=e.get('id','')[6:]
  palettes=uses.get(original,set())
  if len(palettes)!=1:
   # Unused dedicated clan items have no current class assignment, but retain a
   # clan name in their original name/ID (for example Gibraltar leadership gear).
   text=(original+' '+e.get('name','')).lower()
   matches=[c for c in clans.values() if len(c.get('name','').split()[-1])>=4 and c.get('name','').split()[-1].lower() in text]
   if len(matches)==1:
    c=matches[0]; palettes={(c.get('color1'),c.get('color2'),c.get('id'))}
  # A unique owning clan has a well-defined color context. Shared items remain
  # unchanged, rather than incorrectly assigning another clan's palette.
  existing_flags=e.find('Flags')
  if len(palettes)>1 or (not palettes and existing_flags is not None and existing_flags.get('UseTeamColor','').lower()=='true'):
   E.SubElement(root,'SharedItem',id=e.get('id'))
   if existing_flags is None: existing_flags=E.SubElement(e,'Flags')
   existing_flags.set('UseTeamColor','false'); changed=True
   continue
  if len(palettes)!=1: continue
  c1,c2,clan=next(iter(palettes))
  if e.get('Type') not in ['HeadArmor','BodyArmor','Cape','HandArmor','LegArmor','HorseHarness']: continue
  E.SubElement(root,'Item',id=e.get('id'),color1=c1,color2=c2,clan=clan)
  flags=e.find('Flags')
  if flags is None: flags=E.SubElement(e,'Flags')
  flags.set('UseTeamColor','false')
  changed=True; count+=1
 if changed:
  E.indent(tree); tree.write(file,encoding='utf-8',xml_declaration=True)
E.indent(root); E.ElementTree(root).write(DATA/'lab_item_colors.xml',encoding='utf-8',xml_declaration=True)
print('Restored per-item multiplayer color context for',count,'uniquely assigned clan items')
