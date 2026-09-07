// BG-KS-GL-070 仪器使用授权书 · 岗位→仪器 映射（岗前培训考核及授权表 P2 级联数据源）
// 编号基准：以系统仪器库 dept_no 为准（2026-09-08 用户裁定）：
//   1) 安图A6200 → SM-2010（GL-070 原写 SM-1024，库中已停用，作废）
//   2) DXI800 编号以库为准：1=SM-2004、2=SM-2005、3=SM-2006、4=SM-2007（GL-070 原写 3=SM-2005，作废）
export const GL070_POSITIONS = [
  {
    name: '生化流水线岗',
    instruments: [
      { name: '贝克曼生化流水线', code: 'MHZYY-JYK-SM-2001', manager: '朱春阳' },
      { name: '贝克曼AU5821A', code: 'MHZYY-JYK-SM-2002', manager: '朱春阳' },
      { name: '贝克曼AU5821B', code: 'MHZYY-JYK-SM-2003', manager: '夏立娇' },
      { name: '贝克曼DXI800 1', code: 'MHZYY-JYK-SM-2004', manager: '秦东芳' },
      { name: '贝克曼DXI800 2', code: 'MHZYY-JYK-SM-2005', manager: '郑飞' },
      { name: '贝克曼DXI800 3', code: 'MHZYY-JYK-SM-2006', manager: '郑飞' },
      { name: '贝克曼DXI800 4', code: 'MHZYY-JYK-SM-2007', manager: '秦东芳' },
    ],
  },
  {
    name: '急诊岗',
    instruments: [
      { name: '贝克曼AU5800急', code: 'MHZYY-JYK-SM-1005', manager: '张婵媛' },
      { name: '贝克曼DXI800急', code: 'MHZYY-JYK-SM-2008', manager: '赵瑞' },
      { name: '沃芬TOP700C', code: 'MHZYY-JYK-SM-1012', manager: '孔亚龙' },
      { name: '罗氏Cobas e411', code: 'MHZYY-JYK-SM-1018', manager: '王淑华' },
      { name: '西门子RapidPoint 1/2', code: 'MHZYY-JYK-SM-1015/1023', manager: '姚建民' },
      { name: 'FUJI FIMLM DRI-CHEN100', code: 'MHZYY-JYK-SM-1022', manager: '杨静' },
    ],
  },
  {
    name: '病房体检岗',
    instruments: [{ name: '日立HT7600', code: 'MHZYY-JYK-SM-1013', manager: '吕文娟' }],
  },
  {
    name: '糖化电泳岗',
    instruments: [
      { name: '东曹HLC-723G8', code: 'MHZYY-JYK-SM-1021', manager: '姚建民' },
      { name: 'Sebia Capillarys 3 OCTA', code: 'MHZYY-JYK-SM-1026', manager: '杨静' },
      { name: 'Sebia Hydrasys 2', code: 'MHZYY-JYK-SM-1027', manager: '杨静' },
    ],
  },
  {
    name: '凝血流水线岗',
    instruments: [
      { name: '沃芬HemoCELL', code: 'MHZYY-JYK-SM-1009', manager: '孔亚龙' },
      { name: '沃芬TOP700A', code: 'MHZYY-JYK-SM-1010', manager: '孔亚龙' },
      { name: '沃芬TOP700B', code: 'MHZYY-JYK-SM-1011', manager: '孔亚龙' },
      { name: 'Stago CompactMax', code: 'MHZYY-JYK-SM-1028', manager: '孔亚龙' },
    ],
  },
  {
    name: '免疫岗',
    instruments: [
      { name: '罗氏Cobas e601', code: 'MHZYY-JYK-SM-1016', manager: '赵海元' },
      { name: '罗氏Cobas e601A', code: 'MHZYY-JYK-SM-1017', manager: '赵海元' },
      { name: '贝克曼DXI800唐', code: 'MHZYY-JYK-SM-2009', manager: '金子铮' },
      { name: '安图A6200', code: 'MHZYY-JYK-SM-2010', manager: '金子铮' },
      { name: '爱康 URANUS AE 115', code: 'MHZYY-JYK-SM-1025', manager: '徐晓琳' },
    ],
  },
  {
    name: '质谱岗',
    instruments: [{ name: '超高效液相色谱串联质谱系统', code: 'MHZYY-JYK-SM-1032', manager: '赵瑞' }],
  },
  {
    name: '生免一体机岗',
    instruments: [{ name: '迈瑞生免一体机', code: 'MHZYY-JYK-SM-2011', manager: '金子铮' }],
  },
]

export const GL070_ALL_INSTRUMENTS = GL070_POSITIONS.flatMap((p) =>
  p.instruments.map((i) => ({ ...i, position: p.name }))
)
