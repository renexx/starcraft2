from sc2.constants import *
from sc2.bot_ai import BotAI, Race
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from sc2.units import Units
from sc2.data import Result
import random


class ReJiBoBot(BotAI):
    NAME: str = "ReJiBoBot"
    """This bot's name"""

    RACE: Race = Race.Protoss

    def __init__(self):
        BotAI.__init__(self)
        self.proxy_built = False
        self.proxy_poss = None;
        self.unit_attack_amount = 10;
        self.scout_location = [[None, False], [None, False], [None, False]];

    async def on_start(self):
        """
        This code runs once at the start of the game
        Do things here before the game starts
        """
        print("Game started")
        self.proxy_poss = self.game_info.map_center.towards(self.enemy_start_locations[0],
                                                            self.game_info.map_size[0] / 10)

    async def on_step(self, iteration: int):
        """
        This code runs continually throughout the game
        Populate this function with whatever your bot should do!
        """

        await self.distribute_workers()
        await self.build_probes()
        await self.build_pylons()
        await self.build_assimilators()
        await self.build_cyber_core()
        await self.build_four_gateways()
        await self.train_stalkers()
        await self.chrono_boost()
        await self.warpgate_research()
        await self.attack_procedure()
        await self.morph_warpgate()
        await self.warp_stalkers()
        await self.scouting()

    """Build more probes"""

    async def build_probes(self):
        # Every nexus can take up to 20 probes
        for nexus in self.townhalls.ready:
            if self.workers.amount < self.townhalls.amount * 20 and nexus.is_idle:
                if self.can_afford(UnitTypeId.PROBE):
                    nexus.train(UnitTypeId.PROBE)

    """Build pylons"""

    async def build_pylons(self):
        nexus = self.townhalls.ready.random
        position = nexus.position.towards(self.game_info.map_center, 8)
        if (
                self.supply_left < 4
                and self.already_pending(UnitTypeId.PYLON) == 0
                and self.can_afford(UnitTypeId.PYLON)
                and self.supply_used < 100
        ): await self.build(UnitTypeId.PYLON, near=position)

        """Build proxy pylon"""
        if (
                self.structures(UnitTypeId.GATEWAY).amount == 4
                and not self.proxy_built
                and self.can_afford(UnitTypeId.PYLON)
        ):
            await self.build(UnitTypeId.PYLON, near=self.proxy_poss)
            self.proxy_built = True

    """Building the first gateway"""

    async def build_gateway(self):
        if (4 * self.structures(UnitTypeId.NEXUS).amount > self.structures(UnitTypeId.GATEWAY).amount):
            if (
                    self.structures(UnitTypeId.PYLON).ready
                    and self.can_afford(UnitTypeId.GATEWAY)
                    and not self.structures(UnitTypeId.GATEWAY)
            ):
                pylon = self.structures(UnitTypeId.PYLON).ready.random
                await self.build(UnitTypeId.GATEWAY, near=pylon)

    """ Gas harvesting"""

    async def build_assimilators(self):
        if self.structures(UnitTypeId.GATEWAY):
            for nexus in self.townhalls.ready:
                assimilators = self.vespene_geyser.closer_than(15, nexus)
                for assim in assimilators:
                    if not self.can_afford(UnitTypeId.ASSIMILATOR):
                        break
                    worker = self.select_build_worker(assim.position)
                    if (worker is None):
                        break
                    if (
                            not self.gas_buildings
                            or not self.gas_buildings.closer_than(1, assim)
                    ):
                        worker.build(UnitTypeId.ASSIMILATOR, assim)
                        worker.stop(queue=True)

    """Building cyber core for stalkers"""

    async def build_cyber_core(self):
        if (
                self.structures(UnitTypeId.PYLON).ready
        ):
            pylon = self.structures(UnitTypeId.PYLON).ready.random
            if (
                    self.structures(UnitTypeId.GATEWAY).ready
                    and not self.structures(UnitTypeId.CYBERNETICSCORE)
                    and self.can_afford(UnitTypeId.CYBERNETICSCORE)
                    and self.already_pending(UnitTypeId.CYBERNETICSCORE) == 0
            ):
                await self.build(UnitTypeId.CYBERNETICSCORE, near=pylon)

    """Training new stalkers"""

    async def train_stalkers(self):
        for gateway in self.structures(UnitTypeId.GATEWAY).ready:
            if (
                    self.can_afford(UnitTypeId.STALKER)
                    and gateway.is_idle
            ):
                gateway.train(UnitTypeId.STALKER)

    """Classic 4 gateway strategy"""

    async def build_four_gateways(self):
        if (
                self.structures(UnitTypeId.PYLON).ready
                and self.can_afford(UnitTypeId.GATEWAY)
                and self.structures(UnitTypeId.GATEWAY).amount
                + self.structures(UnitTypeId.WARPGATE).amount < 4
        ):
            pylon = self.structures(UnitTypeId.PYLON).ready.first
            await self.build(UnitTypeId.GATEWAY, near=pylon)

    """Chrono boost"""

    async def chrono_boost(self):
        if self.structures(UnitTypeId.CYBERNETICSCORE).ready:
            cyb_core = self.structures(UnitTypeId.CYBERNETICSCORE).ready.first

        nexus = self.townhalls.ready.random
        if nexus.energy >= 50:
            if not self.structures(UnitTypeId.CYBERNETICSCORE).ready:
                nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, nexus)
            if (
                    self.structures(UnitTypeId.CYBERNETICSCORE).ready
                    and not cyb_core.is_idle
                    and not cyb_core.has_buff(BuffId.CHRONOBOOSTENERGYCOST)
            ):
                nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, cyb_core)

    """Warpgate research"""

    async def warpgate_research(self):
        if (
                self.structures(UnitTypeId.CYBERNETICSCORE).ready
                and self.can_afford(AbilityId.RESEARCH_WARPGATE)
                and self.already_pending_upgrade(UpgradeId.WARPGATERESEARCH) == 0
        ):
            cyb_core = self.structures(UnitTypeId.CYBERNETICSCORE).ready.random
            cyb_core.research(UpgradeId.WARPGATERESEARCH)

    """Attack"""

    async def attack_procedure(self):
        stalkercount = self.units(UnitTypeId.STALKER).amount
        stalkers = self.units(UnitTypeId.STALKER).ready
        enemies: Units = self.enemy_units | self.enemy_structures
        enemy_fighters = self.enemy_units.filter(lambda unit: unit.can_attack) + self.enemy_structures(
            {UnitTypeId.BUNKER, UnitTypeId.SPINECRAWLER, UnitTypeId.PHOTONCANNON}
        )
        if stalkercount > self.unit_attack_amount:
            for stalker in stalkers:
                if enemy_fighters:
                    enemies_in_range = enemy_fighters.in_attack_range_of(stalker)
                    if (enemies_in_range):
                        lowest_hp = min(enemies_in_range, key=lambda e: (e.health + e.shield, e.tag))
                        self.micro_attack(stalker, lowest_hp)
                    else:
                        self.micro_attack(stalker, enemy_fighters.closest_to(stalker))
                elif enemies:
                    self.micro_attack(stalker, enemies.random)
                else:
                    self.micro_attack(stalker, self.enemy_start_locations[0])
        else:
            for stalker in stalkers:
                stalker.attack(self.proxy_poss.random_on_distance(3))

    """Micro attack"""

    def micro_attack(self, stalker, enemy):
        if stalker.weapon_cooldown == 0:
            stalker.attack(enemy)
        else:
            stalker.move(self.start_location)

    """Morph warpgate"""

    async def morph_warpgate(self):
        for gateway in self.structures(UnitTypeId.GATEWAY).ready.idle:
            if self.already_pending_upgrade(UpgradeId.WARPGATERESEARCH) == 1:
                gateway(AbilityId.MORPH_WARPGATE)

    """Warp stalkers"""

    async def warp_stalkers(self):
        for warpgate in self.structures(UnitTypeId.WARPGATE).ready:
            abilities = await self.get_available_abilities(warpgate)
            if (
                    AbilityId.WARPGATETRAIN_STALKER in abilities
                    and self.can_afford(UnitTypeId.STALKER)
            ):
                placement = self.proxy_poss.position.random_on_distance(3)
                warpgate.warp_in(UnitTypeId.STALKER, placement)

    """Scounting for enemies"""

    async def scouting(self):
        if (
                self.units(UnitTypeId.ZEALOT).amount < 4
                and self.supply_used > 50
                and self.already_pending(UnitTypeId.ZEALOT) < 4
                and self.can_afford(UnitTypeId.ZEALOT)
        ):
            if self.structures(UnitTypeId.GATEWAY).ready.amount > 0:
                self.structures(UnitTypeId.GATEWAY).ready.random.build(UnitTypeId.ZEALOT)
            elif self.structures(UnitTypeId.WARPGATE).ready.amount > 0:
                self.structures(UnitTypeId.WARPGATE).ready.random.build(UnitTypeId.ZEALOT)

        if self.units(UnitTypeId.ZEALOT).amount > 0:
            zealot = self.units(UnitTypeId.ZEALOT).ready.random
            if zealot.is_idle:
                for minF in self.scout_location:
                    if not minF[1]:
                        minF[0] = random.choice(self.mineral_field)
                        minF[1] = True
                        zealot.move(minF[0])
                        break
            else:
                for minF in self.scout_location:
                    if minF[0] and zealot.position.is_closer_than(10, minF[0]):
                        minF[1] = False
                        zealot.stop()
                        break

    async def on_end(self, result: Result):
        """
        This code runs once at the end of the game
        Do things here after the game ends
        """
        print("Game ended.")
