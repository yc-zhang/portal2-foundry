"""Build Hello Rex, a 1950s Aperture gel test, using stock Portal 2 assets."""
from pathlib import Path

from srctools import Vec
from srctools.vmf import Output, VMF


STEEL = "metal/underground_wall_metal004a"
RIBBED = "metal/underground_metal_corrugated001"
WOOD = "wood/underground_plywood_01a"
WHITE = "tile/underground_white_tile002a"
FLOOR = "tile/underground_black_tile_002a"
CEILING = "concrete/underground_concrete_ceiling001"
TRIGGER = "tools/toolstrigger"
NODRAW = "tools/toolsnodraw"


def build():
    vmf = VMF()
    vmf.spawn.update(paintinmap="1", maxblobcount="250", skyname="sky_black_nofog",
                     message="Hello Rex")

    def point(cls, name, pos, **keys):
        return vmf.create_ent(cls, targetname=name, origin=Vec(*pos), **keys)

    def box(lo, hi, mat):
        prism = vmf.make_prism(Vec(*lo), Vec(*hi), mat=mat)
        vmf.add_brush(prism.solid)
        return prism

    def volume(cls, name, lo, hi, mat, **keys):
        ent = point(cls, name, (Vec(*lo) + Vec(*hi)) / 2, **keys)
        ent.solids.append(vmf.make_prism(Vec(*lo), Vec(*hi), mat=mat).solid)
        return ent

    def wire(ent, event, target, action, param="", delay=0):
        ent.add_out(Output(event, target, action, param, delay))

    def title(name, message, y=0.75):
        point("game_text", name, (0, -600, 240), message=message, x="-1", y=str(y),
              color="255 198 118", channel="2", fadein="0.3", fadeout="0.7",
              holdtime="5", spawnflags="1")

    def doorway(y, halfwidth):
        box((-640, y, 16), (-halfwidth, y+16, 384), WOOD)
        box((halfwidth, y, 16), (640, y+16, 384), WOOD)
        box((-halfwidth, y, 184), (halfwidth, y+16, 384), RIBBED)

    def lift_room(ymin, ymax, bottom, top):
        box((-640,ymin,bottom-16), (640,ymax,bottom), STEEL)
        box((-640,ymin,top), (640,ymax,top+16), CEILING)
        for x in (-656,640):
            box((x,ymin,bottom-16), (x+16,ymax,top+16), RIBBED)

    # The two SDK lifts have real cages, split doors and train paths.
    lift_room(-1472,-896,-1088,448)
    lift_room(-896,1344,-176,384)
    lift_room(1344,1920,-272,2608)
    box((-656,-1488,-1104),(656,-1472,464), RIBBED)
    box((-656,1920,-288),(656,1936,2624), RIBBED)
    for y, low, high in ((-896,-1088,448),(1344,-272,2608)):
        box((-640,y,low),(640,y+16,-176), RIBBED)
        box((-640,y,384),(640,y+16,high), RIBBED)
        doorway(y,96)
    # Close the vertical step on the deep side at the northern seam.
    box((-640,1328,384),(640,1344,2608), RIBBED)
    box((-640,1328,-272),(640,1344,-176), RIBBED)
    # Approach decks stop short of each moving cage.
    box((-112,-1050,-8),(112,-880,16), FLOOR)
    box((-112,1344,-8),(112,1512,16), FLOOR)
    for typ, pos, yaw in (("entrance",(0,-1152,0),180),("exit",(0,1600,0),0)):
        point("func_instance",typ,pos,file=f"instances/underground/test_dome_{typ}_lift_01.vmf",
              angles=f"0 {yaw} 0",fixup_style="0")
    point("info_player_start","arrival",(0,-1152,-347),angles="0 90 0")
    point("weapon_portalgun","portal_device",(0,-966,31),CanFirePortal1="1",CanFirePortal2="1")

    # Flat, continuous brush surfaces accept gel. Only the bleached panels take portals.
    box((-640,-896,-176),(640,128,16), FLOOR)
    box((-640,560,-176),(640,1360,16), WHITE)
    for x in (-220,220):
        box((x-88,-860,16),(x+88,-684,20), WHITE)
    water = box((-640,128,-176),(640,560,-64), NODRAW)
    water.top.mat = "liquids/water_underground_cave"
    volume("trigger_hurt","reservoir",(-640,128,-174),(640,560,-58),TRIGGER,
           damage="1000",damagetype="16384",spawnflags="1")
    # A portal on this ceiling panel drops displaced sentries directly into the reservoir.
    box((-192,216,366),(192,504,384), WHITE)
    # Protected observation galleries, with low slits for aiming at both sentry rows.
    for lo, hi in ((-640,-112),(112,640)):
        for i in range(8):
            y=-660+i*24
            box((lo,y,16),(hi,y+24,30+i*14), WOOD)
        box((lo,-468,16),(hi,-304,128), WOOD)
        box((lo,-320,128),(hi,-304,158), STEEL)
        box((lo,-320,197),(hi,-304,384), RIBBED)
        # Shots pass through the opening, players stay in the gallery.
        box((lo,-320,158),(hi,-304,197),"tools/toolsplayerclip")
    box((-112,-320,176),(112,-304,384), STEEL)
    def shutter(name, lo, hi):
        return volume("func_door",name,lo,hi,RIBBED,movedir="-90 0 0",
                      speed="140",wait="-1",lip="0",spawnflags="0")
    shutter("runway_shutter",(-112,-320,16),(112,-304,176))
    shutter("exit_shutter",(-96,1344,16),(96,1360,184))

    # Use actual Old Aperture pipe meshes. Local +X points up, out of the room;
    # the outlet is at the model origin and the stream begins just below it.
    for name, x, paint in (("repulsion",-220,0),("propulsion",220,2)):
        point("prop_static",name+"_pipe",(x,-772,228),angles="-90 0 0",
              model="models/props_underground/paint_pipe_industrial001_256a.mdl",solid="6")
        point("info_paint_sprayer",name+"_flow",(x,-772,218),angles="90 0 0",
              PaintType=str(paint),start_active="1",maxblobcount="65",blobs_per_second="20",
              min_speed="430",max_speed="475",blob_spread_radius="10",blob_spread_angle="4",
              AmbientSound="2",RenderMode="0",silent="0",DrawOnly="0")

    # The gate's pressure cycle coats a continuous orange runway and a blue takeoff strip.
    # Players can also redirect the two flowing supplies through their own portals.
    cycle=point("logic_relay","runway_ready",(0,-340,120),spawnflags="1")
    for y in range(-288,33,48):
        point("paint_sphere","speed_line",(0,y,20),paint_type="2",radius="82",alpha_percent="1")
    for x in (-52,0,52):
        point("paint_sphere","bounce_lip",(x,106,20),paint_type="0",radius="46",alpha_percent="1")
    for target, action, delay in (("speed_line","Paint",0),("bounce_lip","Paint",0.15),
                                  ("runway_shutter","Open",0.4),("exit_shutter","Open",0.4),
                                  ("jump_hint","Display",0.5)):
        wire(cycle,"OnTrigger",target,action,delay=delay)

    grid=[(x,y) for y in (740,1010) for x in (-384,-192,0,192,384)]
    count=point("math_counter","sentries_down",(0,620,200),min="0",max=str(len(grid)),startvalue="0")
    wire(count,"OnHitMax","runway_ready","Trigger")
    watch=point("logic_timer","field_watch",(0,620,210),RefireTime="0.5",StartDisabled="0")
    wire(watch,"OnTimer","completion_logic","RunScriptCode",f"CheckField({len(grid)}, 560)")
    wire(count,"OnHitMax","field_watch","Disable")
    point("filter_activator_class","sentry_only",(0,344,160),filterclass="npc_portal_turret_floor")
    pit=volume("trigger_multiple","sentry_drain",(-640,128,-174),(640,560,-52),TRIGGER,
               spawnflags="2",filtername="sentry_only",wait="0.2")
    wire(pit,"OnStartTouch","!activator","FireUser1")
    for num,(x,y) in enumerate(grid,1):
        name=f"sentry_{num}"
        turret=point("npc_portal_turret_floor",name,(x,y,17),angles="0 270 0",spawnflags="512")
        latch=point("logic_relay",name+"_down",(x,y,120),spawnflags="1")
        for event in ("OnTipped","OnExplode","OnUser1","OnDeath"):
            wire(turret,event,name+"_down","Trigger")
        wire(latch,"OnTrigger","sentries_down","Add","1")
        wire(latch,"OnTrigger",name,"Disable")
        wire(latch,"OnTrigger",name,"Kill",delay=1.5)

    # Riveted wall bays, overhead girders and warm practical fixtures on both banks.
    for y in (-780,-548,-96,350,680,944,1200):
        box((-640,y,348),(640,y+12,370), STEEL)
        for side in (-1,1):
            x=side*620
            box((x-8,y,-50),(x+8,y+18,350), STEEL)
            point("prop_static","",(x,y,280),angles=f"0 {180 if side==1 else 0} 0",
                  model="models/props_lights/wall_light_old.mdl",solid="0")
            point("light","",(side*472,y,263),_light="255 213 165 330",_quadratic_attn="1")
    for y in (-850,-160,490,1130):
        point("light","",(0,y,260),_light="223 221 208 280",_quadratic_attn="1")
    point("env_cubemap","",(0,320,160),cubemapsize="1")
    start=point("logic_auto","initialise",(0,-840,96))
    # The stock train's StartForward alone can leave it parked in a standalone map.
    arrival=volume("trigger_once","arrival_dispatch",(-40,-1192,-358),(40,-1112,-224),
                   TRIGGER,spawnflags="1")
    wire(arrival,"OnStartTouch","entrance-entrance_lift_train","SetSpeedReal","120",2)
    for name, clip in (("founder","fifties_intro01"),("caroline","caroline_cave_responses25")):
        point("ambient_generic",name,(0,-900,96),message=f"vo/cavejohnson/{clip}.wav",
              spawnflags="49",health="10",pitch="100",pitchstart="100")
    wire(start,"OnMapSpawn","founder","PlaySound",delay=1)
    wire(start,"OnMapSpawn","caroline","PlaySound",delay=11.9)
    title("map_title","HELLO REX   /   APERTURE SCIENCE INNOVATORS",0.22)
    title("gallery_hint","Route blue gel onto the sentries. Clear both rows to release the runway.")
    title("jump_hint","Runway released. Orange to accelerate. Blue to cross.")
    title("completed","HELLO REX   /   TEST COMPLETE",0.40)
    wire(start,"OnMapSpawn","map_title","Display",delay=1)
    hint=volume("trigger_once","briefing",(-640,-890,16),(640,-680,140),TRIGGER,spawnflags="1")
    wire(hint,"OnStartTouch","gallery_hint","Display",delay=1)
    pti=point("func_instance","pti",(0,-580,230),file="instances/p2editor/global_pti_ents.vmf")
    pti.fixup["$disable_pti_audio"]="1"
    finish=volume("trigger_once","cabin_arrival",(-36,1602,18),(36,1644,142),TRIGGER,spawnflags="1")
    point("logic_script","completion_logic",(0,1600,180),vscripts="foundry/hello_rex.nut")
    point("point_clientcommand","local_end",(0,1600,190))
    wire(finish,"OnStartTouch","completed","Display",delay=1)
    wire(finish,"OnStartTouch","exit-exit_lift_train","SetSpeedReal","120",2.65)
    wire(finish,"OnStartTouch","exit-exit_lift_train","Stop",delay=4)
    wire(finish,"OnStartTouch","completion_logic","RunScriptCode","FinishTest()",4.2)
    return vmf


if __name__ == "__main__":
    with Path(__file__).with_name("hello_rex.vmf").open("w", encoding="utf8") as file:
        build().export(file)
