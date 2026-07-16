import json

sops = json.load(open('sop_index.json', encoding='utf-8'))

def find(*frags, exclude=None):
    for s in sops:
        t = s['title']
        if all(f in t for f in frags):
            if exclude and exclude in t:
                continue
            return s['media_id'], t
    return None, None

R = {}
R[125]=find('凝血酶原时间')
R[126]=find('活化部分凝血活酶')
R[127]=find('凝血酶时间')
R[128]=find('纤维蛋白原', exclude='降解')
R[129]=find('D-二聚体')
R[130]=find('纤维蛋白及纤维蛋白原降解产物')
R[131]=find('抗凝血酶')
R[132]=find('蛋白C')
R[133]=find('蛋白S')
R[134]=find('纤溶酶原')
R[135]=find('狼疮抗凝物SCT')
R[136]=find('狼疮抗凝物dRVVT')
R[137]=find('抗Xa')
R[138]=find('vWF')
R[139]=find('钠离子')
R[140]=find('钾离子')
R[141]=find('氯离子')
R[142]=find('血清葡萄糖')
R[143]=find('血清尿素')
R[144]=find('血清肌酐')
R[145]=find('血清尿酸')
R[146]=find('总钙')
R[147]=find('镁')
R[148]=find('血清磷')
R[149]=find('淀粉酶')
R[150]=find('尿或脑脊液总蛋白')
R[151]=find('尿或脑脊液总蛋白')
R[152]=find('氯离子')
R[153]=find('血清葡萄糖')
R[154]=find('尿或脑脊液总蛋白')
R[155]=find('血清白蛋白')
R[156]=find('腺苷脱氨酶')
R[157]=find('乳酸脱氢酶')
R[158]=find('血清葡萄糖')
R[159]=find('糖化血红蛋白')
R[160]=find('β2-微球蛋白')
R[161]=find('终点法全血血氨')
R[162]=find('17-羟')
R[163]=find('17-酮')
R[164]=find('香草扁桃酸')
R[165]=find('血气')
R[166]=find('蛋白电泳')
R[167]=find('免疫固定电泳')
R[168]=find('IgG4')
R[169]=find('三型前胶原') if find('三型前胶原')[0] else find('PIIINP')
R[170]=(None,None)
R[171]=find('透明质酸')
R[172]=(None,None)
R[173]=find('TRUST') or find('梅毒非特异性')
R[174]=find('CEA') or find('癌胚抗原')
R[175]=find('甲型肝炎','IgM')
R[176]=find('风疹','Rub IgM') or find('风疹病毒','IgM')
R[177]=find('巨细胞病毒','IgM')
R[178]=find('巨细胞病毒','IgG')
R[179]=find('风疹','Rub IgG') or find('风疹病毒','IgG')
R[180]=find('弓形虫','IgM')
R[181]=find('弓形虫','IgG')
R[182]=find('单纯疱疹病毒1型','IgG') or find('HSV-1','IgG')
R[183]=find('单纯疱疹病毒2型','IgG') or find('HSV-2','IgG')
R[184]=find('β-胶原') or find('β-CTx')
R[185]=find('戊型肝炎','IgG')
R[186]=find('戊型肝炎','IgM')
R[187]=find('结核') or find('T细胞')
R[188]=find('血管紧张素II') or find('血管紧张素Ⅱ')
R[189]=find('醛固酮')
R[190]=find('促肾上腺皮质激素')
R[191]=find('肾素')
R[192]=find('血浆皮质醇') or find('皮质醇', exclude='游离')
R[193]=find('游离皮质醇')
R[194]=find('人类免疫缺陷病毒','胶体金') or find('人类免疫缺陷病毒抗体测定标准操作程序')
R[195]=find('梅毒','胶体金') or find('梅毒特异性抗体金')
R[196]=find('乙肝表面抗原','胶体金') or find('HBsAg','胶体金')
R[197]=find('丙型肝炎','胶体金') or find('HCV','胶体金')
R[198]=find('单纯疱疹病毒1型','IgM')
R[199]=(None,None)
R[200]=find('肺癌自身抗体') or find('七种肺癌')
R[201]=find('红细胞生成素') or find('EPO')
R[202]=(None,None)
R[203]=(None,None)
R[204]=find('腺苷脱氨酶')
R[205]=find('乳酸脱氢酶')

resolved = {}
for pid,(mid,title) in R.items():
    resolved[pid] = {"media_id": mid, "sop_title": title} if mid else None

json.dump(resolved, open('resolved.json','w'), ensure_ascii=False, indent=1)

have = [k for k,v in resolved.items() if v]
none = [k for k,v in resolved.items() if not v]
mids = sorted(set(v['media_id'] for v in resolved.values() if v))
print(f"有SOP: {len(have)}  无SOP(待查说明书): {len(none)} -> {none}")
print(f"需fetch的独特SOP数: {len(mids)}")
for pid in none:
    print("  无SOP:", pid, [p['name'] for p in json.load(open('tmp_pending81.json',encoding='utf-8')) if p['id']==pid])
