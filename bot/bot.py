from sc2.bot_ai import BotAI, Race
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2
from sc2.player import Bot, Computer
from sc2.data import Result, Difficulty
import random


class CompetitiveBot(BotAI):
    NAME: str = "CompetitiveBot"
    """This bot's name"""

    RACE: Race = Race.Protoss
    """This bot's Starcraft 2 race.
    Options are:
        Race.Terran
        Race.Zerg
        Race.Protoss
        Race.Random
    """

    def __init__(self):
        BotAI.__init__(self)
        self.proxy_built = False
        self.proxy_poss = None;
        self.unit_attack_amount = 6;

    async def on_start(self):
        """
        This code runs once at the start of the game
        Do things here before the game starts
        """
        print("Game started")
        self.proxy_poss = self.game_info.map_center.towards(self.enemy_start_locations[0], 20)

    async def on_step(self, iteration: int):
        """
        This code runs continually throughout the game
        Populate this function with whatever your bot should do!
        """

        await self.distribute_workers()
        await self.build_workers()
        await self.build_pylons()
        # await self.build_gateway()
        await self.build_assimilator()
        await self.build_cyber_core()
        await self.build_other_gateways()
        await self.train_stalkers()
        await self.chrono_boost()
        await self.warpgate_research()
        await self.attack_procedure()
        await self.warp_stalkers()
        await self.micro()
        await self.expansion()

        # print(f"{iteration}, n_workers: {self.workers.amount}, n_idle_workers: {self.workers.idle.amount},", \
        #       f"minerals: {self.minerals}, gas: {self.vespene}, cannons: {self.structures(UnitTypeId.PHOTONCANNON).amount},", \
        #       f"pylons: {self.structures(UnitTypeId.PYLON).amount}, nexus: {self.structures(UnitTypeId.NEXUS).amount}", \
        #       f"gateways: {self.structures(UnitTypeId.GATEWAY).amount}, cybernetics cores: {self.structures(UnitTypeId.CYBERNETICSCORE).amount}", \
        #       f"stargates: {self.structures(UnitTypeId.STARGATE).amount}, voidrays: {self.units(UnitTypeId.VOIDRAY).amount}, supply: {self.supply_used}/{self.supply_cap}")

    async def build_workers(self):
        nexus = self.townhalls.ready.random
        if (
                self.can_afford(UnitTypeId.PROBE)
                and nexus.is_idle
                and self.workers.amount < self.townhalls.amount * 20
        ):
            nexus.train(UnitTypeId.PROBE)

    async def build_pylons(self):
        nexus = self.townhalls.ready.random
        position = nexus.position.towards(self.enemy_start_locations[0], 10)
        if (
                self.supply_left < 3
                and self.already_pending(UnitTypeId.PYLON) == 0
                and self.can_afford(UnitTypeId.PYLON)
        ): await self.build(UnitTypeId.PYLON, near=position)

        # build proxy pylon
        if (
                self.structures(UnitTypeId.GATEWAY).amount == 4
                and not self.proxy_built
                and self.can_afford(UnitTypeId.PYLON)
        ):
            await self.build(UnitTypeId.PYLON, near=self.proxy_poss)
            self.proxy_built = True

    # Building the first gateway
    async def build_gateway(self):
        if (4 * self.structures(UnitTypeId.NEXUS).amount > self.structures(UnitTypeId.GATEWAY).amount):
            if (
                    self.structures(UnitTypeId.PYLON).ready
                    and self.can_afford(UnitTypeId.GATEWAY)
                    and not self.structures(UnitTypeId.GATEWAY)
            ):
                pylon = self.structures(UnitTypeId.PYLON).ready.random
                await self.build(UnitTypeId.GATEWAY, near=pylon)

    # Gas harvesting
    async def build_assimilator(self):
        if (
                self.structures(UnitTypeId.GATEWAY)
        ):
            for nexus in self.townhalls.ready:
                assims = self.vespene_geyser.closer_than(15, nexus)
                for assim in assims:
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

    # Building cyber core for stalkers
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

    # Training new stalkers
    async def train_stalkers(self):
        for gateway in self.structures(UnitTypeId.GATEWAY).ready:
            if (
                    self.can_afford(UnitTypeId.STALKER)
                    and gateway.is_idle
            ):
                gateway.train(UnitTypeId.STALKER)

    # Classic 4 gateway strategy
    async def build_other_gateways(self):
        if (
                self.structures(UnitTypeId.PYLON).ready
                and self.can_afford(UnitTypeId.GATEWAY)
                and self.structures(UnitTypeId.GATEWAY).amount
                + self.structures(UnitTypeId.WARPGATE).amount < 4
        ):
            pylon = self.structures(UnitTypeId.PYLON).ready.first
            await self.build(UnitTypeId.GATEWAY, near=pylon)

    async def chrono_boost(self):
        if self.structures(UnitTypeId.PYLON).amount > 0:
            nexus = self.townhalls.ready.random
            if nexus.energy >= 50:
                if not self.structures(UnitTypeId.CYBERNETICSCORE).ready:
                    nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, nexus)
                else:
                    cybercore = self.structures(UnitTypeId.CYBERNETICSCORE).ready.random
                    nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, cybercore)

    async def warpgate_research(self):
        if (
                self.structures(UnitTypeId.CYBERNETICSCORE).ready
                and self.can_afford(AbilityId.RESEARCH_WARPGATE)
                and self.already_pending_upgrade(UpgradeId.WARPGATERESEARCH) == 0
        ):
            cybercore = self.structures(UnitTypeId.CYBERNETICSCORE).ready.random
            cybercore.research(UpgradeId.WARPGATERESEARCH)

    async def attack_procedure(self):
        stalkercount = self.units(UnitTypeId.STALKER).amount
        stalkers = self.units(UnitTypeId.STALKER).ready.idle

        for stalker in stalkers:
            if stalkercount > self.unit_attack_amount:
                stalker.attack(self.enemy_start_locations[0])
            else:
                stalker.attack(self.proxy_poss.random_on_distance(3))

    async def warp_stalkers(self):
        for warpgate in self.structures(UnitTypeId.WARPGATE).ready:
            abilities = await self.get_available_abilities(warpgate)
            if (
                    AbilityId.WARPGATETRAIN_STALKER in abilities
                    and self.can_afford(UnitTypeId.STALKER)
            ):
                placement = self.proxy_poss.position.random_on_distance(3)
                warpgate.warp_in(UnitTypeId.STALKER, placement)

    async def micro(self):
        stalkers = self.units(UnitTypeId.STALKER)
        enemy_location = self.enemy_start_locations[0]

        if self.proxy_built:
            for stalker in stalkers:
                if stalker.weapon_cooldown == 0 and stalkers.amount > self.unit_attack_amount:
                    stalker.attack(enemy_location)
                elif stalker.weapon_cooldown < 0:
                    stalker.move(self.proxy_poss)
                else:
                    stalker.move(self.proxy_poss)

    async def expansion(self):
        if self.can_afford(UnitTypeId.NEXUS):
            await self.expand_now()

    async def on_end(self, result: Result):
        """
        This code runs once at the end of the game
        Do things here after the game ends
        """
        print("Game ended.")
