from secret import token, appid
from urls import arrivals_url, vehicle_loc_url, alert_url, route_config_url
import discord
from discord.ext import tasks, commands
from discord.commands import option 
import requests
import pandas
import json

ROUTES_LIST = []
STOPS_LIST = []

intents = discord.Intents.default()

bot = discord.Bot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

def generate_route_ids_alerts() -> dict:
    return_dict = {}
    r = requests.get(f"{alert_url}/appID/{appid}")
    data = r.json()
    if data.get('resultSet') is None:
        return None
    alerts = data['resultSet'].get('alert')
    for item in alerts:
        route = item.get('route')
        print(route)
        if route is not None:
            for route_item in route:
                return_dict.update({route_item.get('desc'):route_item.get('id')})
    return return_dict

def generate_stop_id_list(id_list) -> dict:
    stop_id_dict = {}
    route_stop_dict = {}

    for id in id_list:
        r = requests.get(f"{route_config_url}/route/{id}/dir/true/stops/true/appid/{appid}/json/true")
        resultSet = r.json().get('resultSet')
        if resultSet.get('errorMessage') is not None:
            print(resultSet.get('errorMessage'))
            return None
        data = resultSet['route']
        for item in data:
            item_list = item['dir']
            print(item_list)
            print(len(item_list))
            for stops in item_list:
                print(stops)
                stop_list = stops.get('stop')
                for stop in stop_list:
                    
                    print(stop)
                    stop_id_dict.update({stop.get('desc'):stop.get('locid')})
    return stop_id_dict


            



        


ID_DICT = generate_route_ids_alerts()
ROUTES_LIST = list(ID_DICT.keys())

STOP_ID_LIST = generate_stop_id_list(list(ID_DICT.values()))
STOP_LIST = list(STOP_ID_LIST.keys())

print(STOP_ID_LIST.keys())

class TriMet(commands.Cog):
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot


    
    @commands.slash_command()
    @option("route", description="Name of the Route", autocomplete=discord.utils.basic_autocomplete(ROUTES_LIST))
    async def alerts(self, ctx, route):
        print("Alert Function Called")
        route_id = ID_DICT.get(route)
        alerts_list = []
        global_alerts = []
        r = requests.get(f"{alert_url}/appID/{appid}/routes/{route_id}")
        resultSet = r.json().get('resultSet')
        if resultSet is None:
            await ctx.respond("Error proccesing command")
            return
        error = resultSet.get('errorMessage')
        if error is not None:
            await ctx.respond(f"Error with message: {error}")
            return
        alerts = resultSet.get('alert')
        for alert in alerts:
            if alert.get('system_wide_flag') is True:
                temp = {}
                temp.update({"info_link_url":alert.get('info_link_url')})
                temp.update({"end":alert.get("end")})
                temp.update({"begin":alert.get('begin')})
                temp.update({"header_text":alert.get('header_text')})
                temp.update({"desc":alert.get('desc')})

                global_alerts.append(temp)
            else:
                temp = {}
                temp.update({'end':alert.get('end')})
                temp.update({'begin':alert.get('begin')})
                temp.update({'info_link_url':alert.get('info_link_url')})
                temp.update({'desc':alert.get('desc')})
                alerts_list.append(temp)
        print(global_alerts)
        embed_list = []
        for global_alert in global_alerts:
            print("going through global alerts")
            if global_alert.get('info_link_url') is None:
                global_embed = discord.Embed(title=global_alert.get('header_text'), description=global_alert.get('desc'))
            else:
                global_embed = discord.Embed(title=global_alert.get('header_text'), description=global_alert.get('desc'), url=global_alert.get('info_link_url'))
            global_embed.add_field(name="Began", value=f"<t:{str(global_alert.get('begin'))[:10]}:R>")
            global_embed.add_field(name="Ends", value=f"<t:{str(global_alert.get('end'))[:10]}:R>")
            embed_list.append(global_embed)
        
        for item in alerts_list:
            if item.get('info_link_url') is None:
                alert_embed = discord.Embed(title=f"{route} Alerts", description=item.get('desc'))
            else:
                alert_embed = discord.Embed(title=f"{route} Alerts", description=item.get('desc'), url=item.get('info_link_url'))
            alert_embed.add_field(name="Began", value=f"<t:{str(item.get('begin'))[:10]}:R>")
            alert_embed.add_field(name="Ends", value=f"<t:{str(item.get('end'))[:10]}:R>")
            embed_list.append(alert_embed)
        await ctx.respond(embeds=embed_list[:10])

    @commands.slash_command()
    @option("stop", description="Name of the Stop", autocomplete=discord.utils.basic_autocomplete(STOP_LIST))
    async def schedule(self, ctx, stop):
        stop_id = STOP_ID_LIST.get(stop)
        r = requests.get(f"{arrivals_url}/appid/{appid}/locIDs/{stop_id}")
        resultSet = r.json().get('resultSet')
        if resultSet.get('errorMessage') is not None:
            await ctx.respond(resultSet.get('errorMessage'))
            return
        print(resultSet)
        arrival = resultSet.get('arrival')
        print(f"\narrival: {arrival}")
        arrival_list = []
        for item in arrival:
            print(f"\n{item}")
            temp = {}
            temp.update({'scheduled':item.get('scheduled')})
            temp.update({'departed':item.get('departed')})
            temp.update({'status':item.get('status')})
            if item.get('detoured') is not None:
                temp.update({'detour':item.get('detour')})
            arrival_list.append(temp)
        print(arrival_list)

        message_embed = discord.Embed(title=stop)
        for arrival_info in arrival_list:
            title = f"Arriving: <t:{str(arrival_info.get('scheduled'))[:10]}:R>"
            if arrival_info.get('detour') is not None:
                detour = resultSet.get('detour')
                if detour is None:
                    body = "Detoured"
                else:
                    detourid = arrival_info.get('detour')
                    for detour_item in detour:
                        if check_list(detour_item.get('id'),detourid):
                            body = f"Detoured: {detour_item.get('desc')}"
            else:
                body = f"Status: {arrival_info.get('status')}"
            message_embed.add_field(name=title, value=body)
        
        await ctx.respond(embed= message_embed)


def check_list(id, list):
    for item in list:
        if item == id:
            return True
    return False










    








bot.add_cog(TriMet(bot))
bot.run(token)