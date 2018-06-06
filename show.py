# -*- coding: utf-8 -*-

from plotly.offline import download_plotlyjs, plot
import plotly.plotly as py
import plotly.graph_objs as go
import config

py.sign_in(config.plotly_username,config.plotly_key)

def generateData(data):
    binNames_list = []
    binResult_list  = []
    for item in sorted(data, key=data.get, reverse=False):
        if data[item] <= 2:
            continue
        binNames_list.append(str(item) + ' ({0})'.format(data[item]))
        binResult_list.append(str(data[item]))
    return  {
            "values": binResult_list,
            "labels": binNames_list,
            #"domain": {"x": [0, .48]},
            #"name": "GHG Emissions",
            "hoverinfo":"label+percent+value",
            #"hole": .4,
            "type": "pie"
    }

def generatePlot(dataList, name):
    fig = {
        "data": [ dataList ],
        "layout": { "title": name, } # (except rare tags like `songs that you wanna listen to over and over again`)
    }
    plot(fig, filename="genre.html",auto_open=False)
    py.image.save_as(fig, filename="genre.png")
    print("ALL generated")

def magic(inputData, name = 'Music statistic'):
    generatePlot(generateData(inputData), name)

if __name__ == "__main__":
    magic(tagsInputData, name = 'Music statistic (using Gracenote DB) (w/o 1-2)')