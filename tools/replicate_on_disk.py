import ast, json, math, os, sys
from collections import Counter
D = '/datasets/nuscenes-full/v1.0-trainval'
def L(n): return json.load(open(os.path.join(D, n)))
cat={c['token']:c['name'] for c in L('category.json')}
inst={i['token']:cat[i['category_token']] for i in L('instance.json')}
samp={s['token']:s['scene_token'] for s in L('sample.json')}
scn={s['token']:s['name'] for s in L('scene.json')}
vis={v['token']:v['level'] for v in L('visibility.json')}
sen={s['token']:s['channel'] for s in L('sensor.json')}
csc={c['token']:sen[c['sensor_token']] for c in L('calibrated_sensor.json')}
ego={e['token']:e['translation'] for e in L('ego_pose.json')}
se={sd['sample_token']:ego[sd['ego_pose_token']] for sd in L('sample_data.json')
    if sd['is_key_frame'] and csc.get(sd['calibrated_sensor_token'])=='LIDAR_TOP'}
VAL=set(json.load(open('val_scenes.json')))
DET={'movable_object.barrier':'barrier','vehicle.bicycle':'bicycle','vehicle.bus.bendy':'bus',
 'vehicle.bus.rigid':'bus','vehicle.car':'car','vehicle.construction':'construction_vehicle',
 'vehicle.motorcycle':'motorcycle','human.pedestrian.adult':'pedestrian',
 'human.pedestrian.child':'pedestrian','human.pedestrian.construction_worker':'pedestrian',
 'human.pedestrian.police_officer':'pedestrian','movable_object.trafficcone':'traffic_cone',
 'vehicle.trailer':'trailer','vehicle.truck':'truck'}
R={'car':50,'truck':50,'bus':50,'trailer':50,'construction_vehicle':50,'pedestrian':40,
   'motorcycle':40,'bicycle':40,'traffic_cone':30,'barrier':30}
surv=0; killed=0; v80=0; bands=Counter(); bk=Counter()
for a in L('sample_annotation.json'):
    st=samp[a['sample_token']]
    if scn[st] not in VAL: continue
    d=DET.get(inst[a['instance_token']])
    if d is None: continue
    e=se[a['sample_token']]; t=a['translation']
    dist=math.hypot(t[0]-e[0], t[1]-e[1])
    if dist>=R[d]: continue
    b='0-20m' if dist<20 else ('20-30m' if dist<30 else ('30-40m' if dist<40 else '40-50m'))
    surv+=1; bands[b]+=1
    if a['num_lidar_pts']+a['num_radar_pts']==0:
        killed+=1; bk[b]+=1
        if vis.get(a.get('visibility_token',''))=='v80-100': v80+=1
print(f'REPLICATION on independently obtained copy (/datasets/nuscenes-full)')
print(f'surviving distance filter : {surv:,}')
print(f'removed by point filter   : {killed:,}  ({100*killed/surv:.2f}%)')
print(f'  of which v80-100        : {v80:,}')
for b in ['0-20m','20-30m','30-40m','40-50m']:
    ne=bands[b]-bk[b]
    print(f'  {b:<8} N_full={bands[b]:>7,}  removed={bk[b]:>6,}  inflation=x{bands[b]/ne:.4f}')
