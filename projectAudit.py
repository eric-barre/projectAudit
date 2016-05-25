#!/usr/bin/env python

##########################################################################
# This script extract audit information about the project. Such as project name, author, created date
# It also documents all the steps that are part of the project along with
# any computed formulae used


import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import ConnectionError
import argparse
import os
import sys
import json
import re
import pdfkit

######END POINTS######
LIBRARY_ENDPOINT = '/rest/library/data'
PROJECT_ENDPOINT = '/rest/projects'
SCRIPT_ENDPOINT = '/rest/scripts?pretty=true'
PUBLISH_ENDPOINT = '/rest/project/publish'
EXPORT_ENDPOINT = '/rest/library/exports'
USER_ENDPOINT = '/rest/users'

######Globals######
html_page_start = '<HTML><head><style>table {page-break-inside: avoid !important;}.left {float:left;width:100px;height: 20px;} body {margin:10;padding:10}.page-break	{ display: block; page-break-before: always; }.block {text-align: center;margin: 20px;}.block:before {content: "\\200B";display: inline-block;height: 100%; vertical-align: middle;}.blockcentered {display: inline-block;vertical-align: middle;width: 300px;padding: 10px 15px;border: #a0a0a0 solid 1px;background: #f5f5f5;}.blockleft {display: inline-block;vertical-align: left;width: 300px;padding: 10px 15px;border: #a0a0a0 solid 1px;background: #f5f5f5;}.caption{text-align: left;font-weight: bold;padding: 10px} .captionErr{text-align: left;font-weight: bold;padding: 10px;color:rgb(204,0,0)}  td{padding: 2px;}</style></head><BODY>'
html_page_end = "</BODY></HTML>"
html_page_title = '<div class="block" style="height: 300px;"><div class="blockcentered"><h1>prjname</h1><p>prjdesc</p><p>Project Owner: prjowner</p><p>Owner email: ownemail</p><p>Creation date: prjcreateddate</p><p>Last Updated date: prjlastupdateddate</p></div></div>'
html_page_break = '<div class="page-break">'
url = ""
authTok = ""

######PDF Options######
options = {
    # 'page-size': 'Letter',
    'margin-top': '0.75in',
    'margin-right': '0.5in',
    'margin-bottom': '0.75in',
    'margin-left': '0.5in',
    # 'encoding': "UTF-8",
    # 'no-outline': None,
    'header-html': 'header.html',
    'header-spacing': 5
}


#####Error Class#####
class AppError(Exception):
    def __init__(self, msg, errcode):
        self.msg = msg
        self.errCode = errcode


def main(argv):
    global authTok
    global url
    global html_page_title

    # TODO: parse the arguments passed using argparse instead of below
    url = argv[1]
    authTok = HTTPBasicAuth(argv[2], argv[3])
    # TODO: get the project based on the id provided
    # testing
    obj = getProjectByName("CustomerProductSegmentation")
    # obj = getProjectByID('a156ee9387de49c9a52aa2595067f89f')
    #obj = getProjectByName('MultiFeed Reconciliation Risk Alerts')
    print '-------------------------'

    # TODO provide a filter on the arg to process project where created ro mod date > that xxxx or owner = xxxx
    # TODO or process all projects.

    # TODO: Start building the HTML with the project info
    html = html_page_start
    projectname = obj.get('name').encode('utf-8')
    projectowner = obj.get('userName').encode('utf-8')
    if getUserInfo(obj.get('userId'))[0]['email'] is not None:
        owneremail = getUserInfo(obj.get('userId'))[0]['email']
    else:
        owneremail = ""
    if obj.get('description') is not None:
        projectdescription = obj.get('description').encode('utf-8')
    else:
        projectdescription = "No description provided for the project."
    projectcreateddate = obj.get('created').encode('utf-8')
    projectlastupdatedate = obj.get('updated').encode('utf-8')
    html_page_title = re.sub("prjname", projectname, html_page_title)
    html_page_title = re.sub("prjowner", projectowner, html_page_title)
    html_page_title = re.sub("ownemail", owneremail, html_page_title)
    html_page_title = re.sub("prjdesc", projectdescription, html_page_title)
    html_page_title = re.sub(
        "prjcreateddate", projectcreateddate, html_page_title)
    html_page_title = re.sub("prjlastupdateddate",
                             projectlastupdatedate, html_page_title)
    html += html_page_title + html_page_break

    # Get the project script. Extract pertinent info from it such as base DS, steps etc...
    # for each DS used get the #rows and name of the DS
    scripts = getProjectScript(obj.get('projectId').encode('utf-8'))
    print scripts[0]
    html += processTopFirstPage(scripts) + \
            processSteps(scripts[0], 0, "") + '</div>' + html_page_end

    # Convert the HTML to PDF
    pdfkit.from_string(html, projectname + ".pdf", options=options)


##############################################################
# processTopFirstPage()
#
#
def processTopFirstPage(scripts):
    numversion = len(scripts) - 1
    numsteps = len(scripts[0]['steps'])
    return '<div class="left" style="width: 100%;"><p><p><p>Number of revisions: ' + str(
        numversion) + '</p><p>Number of steps in the most recent version: ' + str(numsteps) + '</p><hr>'


##############################################################
# processSteps()
#
#
#
def processSteps(script, idx, prtidx):
    html_steps = ""
    for step in script['steps']:
        if type(idx) is str:
            idx = chr(ord(idx) + 1)
        else:
            idx += 1
        if step['type'] == 'AnchorTable':
            html_steps += processDS(step['importStep'],
                                    str(prtidx) + str(idx), "Base")
            html_steps += "</table>"
        elif (step['type'] == 'LookupTable') or (step['type'] == 'Append'):
            html_steps += processDS(step['steps'][0],
                                    str(prtidx) + str(idx), step['type'])
            html_steps += processAttachType(step) + "</table>"
            if len(step['steps']) > 1:
                html_steps += processSteps(step, '`', idx)
        elif step['type'] == 'Import':
            idx = '`'
        elif step['type'] == 'Expression':
            html_steps += processExpression(step, str(prtidx) + str(idx))
        elif step['type'] == 'Transform':
            html_steps += processTransform(step, str(prtidx) + str(idx))
        elif step['type'] == 'ClusterEdit':
            html_steps += processClusterEdit(step, str(prtidx) + str(idx))
        elif step['type'] == 'EditColumns':
            html_steps += processEditColumns(step, str(prtidx) + str(idx))
        elif step['type'] == 'SplitColumn':
            html_steps += processSplitColumns(step, str(prtidx) + str(idx))
        elif step['type'] == 'Pivot':
            html_steps += processPivot(step, str(prtidx) + str(idx))
        elif step['type'] == 'BulkEdit':
            html_steps += processBulkEdit(step, str(prtidx) + str(idx))
        else:
            html_steps += '<p style="font-weight: bold">Step ' + \
                          str(prtidx) + str(idx) + ': ' + step['type']
    return html_steps

##############################################################
# processBulkEdit()
#
#
def processBulkEdit(step, idx):
    html_be_table = makeCaption(step, "Find&Replace", idx)
    html_be_table += '<tr><td>Column name</td><td>' + str(step['columnName']) + '</td></tr>'
    html_be_table += '<tr><td>Original value</td><td>' + str(step['value']) + '</td></tr>'
    html_be_table += '<tr><td>New value</td><td>' + str(step['newValue']) + '</td></tr>'
    html_be_table += '<tr><td>Replace the whole cell value</td><td>' + str(step['replaceWholeCell']) + '</td></tr>'
    html_be_table += '<tr><td>Edit type</td><td>' + step['editType'] + '</td></tr>'

    return html_be_table

##############################################################
# processPivot()
#
#
def processPivot(step, idx):
    html_pvt_table = makeCaption(step, "Shape", idx)
    html_pvt_table += '<tr><td>Shape Type</td><td>shp</td></tr>'
    html_pvt_table = re.sub("shp", step['pivotType'], html_pvt_table)
    if step['pivotType'] == "Unpivot":
        html_pvt_table += '<tr><td>Row labels</td><td>' + ', ' .join(step['anchors']) + '</td></tr>'
        html_pvt_table += '<tr><td>Values</td><td>' + ', '.join(step['columnNames']) + '</td></tr>'
        html_pvt_table += '<tr><td>Column label</td><td>' + step['unpivotColumnName'] + '</td></tr>'
        html_pvt_table += '<tr><td>Value label</td><td>' + step['unpivotMetricName'] + '</td></tr>'
    if step['pivotType'] == 'GroupBy':
        html_pvt_table += '<tr><td>Group by Column(s)</td><td>' + ', ' .join(step['anchors']) + '</td></tr>'
        for agg in step['aggregateFunctions']:
            html_pvt_table += '<tr><td>Aggregate function</td><td>' + agg['aggregateType'] + ' of ' + \
                              agg['columnName'] + '</td></tr>'
            html_pvt_table += '<tr><td>New column name</td><td>' + agg['newColumnName'] + '</td></tr>'
    if step['pivotType'] == "Pivot":
        html_pvt_table += '<tr><td>Row labels</td><td>' + ', '.join(step['anchors']) + '</td></tr>'
        html_pvt_table += '<tr><td>Column labels</td><td>' + ', '.join(step['columnNames']) + '</td></tr>'
        for agg in step['aggregateFunctions']:
            html_pvt_table += '<tr><td>Aggregate function</td><td>' + agg['aggregateType'] + ' of ' + \
                              agg['columnName'] + '</td></tr>'
            html_pvt_table += '<tr><td>New column name</td><td>' + agg['newColumnName'] + '</td></tr>'
    if step['pivotType'] == "Transpose":
        html_pvt_table += '<tr><td>Row values</td><td>' + ', '.join(step['anchors']) + '</td></tr>'
        html_pvt_table += '<tr><td>Column label</td><td>' + ', '.join(step['columnNames']) + '</td></tr>'
    if step['pivotType'] == 'DeDuplicate':
        html_pvt_table += '<tr><td>Deduplicate on Column(s)</td><td>' + ', '.join(step['anchors']) + '</td></tr>'
    return html_pvt_table + '</table>'

##############################################################
# processSplitColumns()
#
#
def processSplitColumns(step, idx):
    html_sc_table = makeCaption(step, "Split Column", idx)
    html_sc_table += '<tr><td>Column name</td><td>colname</td></tr>' \
                    '<tr><td>Split type</td><td>spl</td></tr>' \
                    '<tr><td>Separator</td><td>sep</td></tr>'
    html_sc_table = re.sub("colname", step['columnName'], html_sc_table)
    html_sc_table = re.sub("spl", step['splitType'], html_sc_table)
    html_sc_table = re.sub("sep", step['separator'], html_sc_table)

    if step['splitType'] == 'Regex':
        html_sc_table += '<tr><td>Regular Expression Type</td><td>' + step['regexType'] + '</td></tr>'
        if step['regexOptions'] is not None:
            html_sc_table += '<tr><td>Regular Expression Option</td><td>' + step['regexOptions'] + '</td></tr>'
    if step['splitType'] == 'Length':
        html_sc_table += '<tr><td>Lengths</td><td>' + str(step['splitLengths']) + '</td></tr>'
    html_sc_table += '<tr><td>Number of new columns</td><td>' + str(len(step['newColumns'])) + '</td></tr>'
    listCols = []
    for col in step['newColumns']:
        listCols.append(col['name'])
    html_sc_table += '<tr><td>New column(s)</td><td>' + ', ' .join(listCols) + '</td></tr>'
    if step['publishPoints'] is not None:
        html_sc_table += '<tr><td>Publish Point (Lens)</td><td>' + ','.join(step['publishPoints']) + \
                         '</td></tr></table>'
    else:
        html_sc_table += '</table>'
    return html_sc_table


##############################################################
# processEditColumns()
#
#
def processEditColumns(step, idx):
    html_ec_table = makeCaption(step, "Edit Columns", idx)
    html_ec_table += '<tr><td>Edit type</td><td>edt</td></tr>'
    numHidden = 0
    listCol = []
    for col in step['columns']:
        if not col['active']:
            numHidden += 1
            listCol.append(col['name'])
    if numHidden > 0:
        html_ec_table = re.sub("edt", "Hide column(s)", html_ec_table)
        html_ec_table += '<tr><td>Number of column(s) hidden</td><td>' + str(numHidden) + '</td></tr>'
        html_ec_table += '<tr><td>List of hidden column(s)</td><td>' + ',' .join(listCol) + '</td></tr>'
    else:
        html_ec_table = re.sub("edt", "Move column(s)", html_ec_table)
    if step['publishPoints'] is not None:
        html_ec_table += '<tr><td>Publish Point (Lens)</td><td>' + ','.join(step['publishPoints']) + \
                         '</td></tr></table>'
    else:
        html_ec_table += '</table>'
    return html_ec_table

##############################################################
# processClusterEdit()
#
#
def processClusterEdit(step, idx):
    html_ce_table = makeCaption(step, "Cluster&Edit", idx)
    html_ce_table += '<tr><td>Column Name</td><td>colname</td></tr>' \
                    '<tr><td>Algorithm used</td><td>alg</td></tr>' \
                    '<tr><td>Replace with</td><td>rep</td></tr>'
    html_ce_table = re.sub("colname", step['columnName'], html_ce_table)
    html_ce_table = re.sub("alg", step['algorithm'], html_ce_table)
    if step['outputStrategy'] is not None:
        html_ce_table = re.sub("rep", step['outputStrategy'], html_ce_table)
    else:
        html_ce_table = re.sub("rep", "", html_ce_table)
    if step['publishPoints'] is not None:
        html_ce_table += '<tr><td>Publish Point (Lens)</td><td>' + ','.join(step['publishPoints']) + \
                         '</td></tr></table>'
    else:
        html_ce_table += '</table>'
    return html_ce_table


##############################################################
# processTransform()
#
#
def processTransform(step, idx):
    html_ts_table = makeCaption(step, "Change", idx)
    html_ts_table += '<tr><td>New Column Name</td><td>colname</td></tr><tr><td>Transformation</td><td>ts</td></tr>'
    html_ts_table = re.sub("ts", step['opType'], html_ts_table)
    html_ts_table = re.sub("colname", step['newColumnName'], html_ts_table)
    if step['publishPoints'] is not None:
        html_ts_table += '<tr><td>Publish Point (Lens)</td><td>' + ','.join(step['publishPoints']) + \
                         '</td></tr></table>'
    else:
        html_ts_table += '</table>'
    return html_ts_table


##############################################################
# processExpression()
#
#
def processExpression(step, idx):
    html_ex_table = makeCaption(step, "Compute", idx)
    html_ex_table += '<tr><td>New Column Name</td><td>colname</td></tr>' \
                     '<tr><td>Expression</td><td>exp</td></tr>'
    html_ex_table = re.sub("colname", step['newColumnName'], html_ex_table)
    html_ex_table = re.sub("exp", step['expression'], html_ex_table)
    if step['publishPoints'] is not None:
        html_ex_table += '<tr><td>Publish Point (Lens)</td><td>' + ','.join(
            step['publishPoints']) + '</td> </tr> </table> '
    else:
        html_ex_table += '</table>'
    return html_ex_table


##############################################################
# processAttachType()
# This function add information to the attach step table based
# on the type of attach performed (lookup or append)
#
def processAttachType(obj):
    html_ds_append = '<tr><td>Number of column(s) matching in the Append operation</td><td>matchcnt</td></tr>'
    html_ds_lookup = '<tr><td>Lookup Type</td><td>lkptype</td></tr><tr><td>Left side column(s)</td><td>leftcol</td></tr>' \
                     '<tr><td>Right side column(s)</td><td>rightcol</td></tr>'
    if obj['type'] == 'Append':
        if obj['publishPoints'] is not None:
            html_ds_append += '<tr><td>Publish Point (Lens)</td><td>' + ','.join(
                obj['publishPoints']) + '</td> </tr>'
        return re.sub("matchcnt", str(len(obj['columnPairs'])), html_ds_append)
    else:
        html_ds_lookup = re.sub("lkptype", obj['joinType'], html_ds_lookup)
        html_ds_lookup = re.sub("leftcol", ', '.join(
            obj['sourceJoinColumns']), html_ds_lookup)
        html_ds_lookup = re.sub("rightcol", ', '.join(
            obj['targetJoinColumns']), html_ds_lookup)
        if obj['publishPoints'] is not None:
            html_ds_lookup += '<tr><td>Publish Point (Lens)</td><td>' + ','.join(
                obj['publishPoints']) + '</td> </tr>'
        return html_ds_lookup


##############################################################
# processDS()
# This function creates a table with information regarding a dataset
# Input:    JSON Obj representing the DS, the step index and the step type (AnchorTable of LookupTable)
# Output:   A HTML table
def processDS(step, idx, t):
    obj = getLibraryObject(step['libraryId'])[0]
    html_ds_table = makeCaption(step, t, idx)
    html_ds_table += '<tr><td>Dataset Name</td><td>dsname</td></tr><' \
                     'tr><td>Number of Rows</td><td>dsrowcnt</td></tr>' \
                     '<tr><td>Number of Columns</td><td>dscolcnt</td></tr>' \
                     '<tr><td>Size on Library (in bytes)</td><td>dssize</td></tr>' \
                     '<tr><td>Dataset source type</td><td>dssourcetype</td></tr>' \
                     '<tr><td>Dataset source name</td><td>dssourcename</td></tr>' \
                     '</tr><tr><td>Description</td><td>dsdesc</td></tr></tr>'
    html_ds_table = re.sub("dsname", obj['name'], html_ds_table)
    html_ds_table = re.sub("dsrowcnt", str(obj['rowCount']), html_ds_table)
    html_ds_table = re.sub("dscolcnt", str(obj['columnCount']), html_ds_table)
    html_ds_table = re.sub("dssize", str(obj['size']), html_ds_table)
    html_ds_table = re.sub("dssourcetype", obj['source'][
        'type'], html_ds_table)
    if obj['source']['type'] != 'Script':
        if obj['source']['name'] is not None:
            html_ds_table = re.sub("dssourcename", obj['source'][
                'name'], html_ds_table)
        elif obj['source']['metadata']['name'] is not None:
            html_ds_table = re.sub("dssourcename", obj['source'][
                'metadata']['name'], html_ds_table)
        else:
            html_ds_table = re.sub(
                "dssourcename", "Unable to retrieve source name", html_ds_table)
    else:
        html_ds_table = re.sub("dssourcename", obj['name'], html_ds_table)
    dsdesc = "No description available."
    if obj['description'] is not None:
        dsdesc = obj['description']
    html_ds_table = re.sub("dsdesc", dsdesc, html_ds_table)
    return html_ds_table + '<p>'


##############################################################
# getLibraryObject()
# This function returns JSON object for the specified dataset UID
# Input:    dataset UID
# Returns:  The JSON Object representing the dataset
# Throws:   AppError if the object does not exist or the request
# status_code is not 200
def getLibraryObject(uid):
    try:
        return executeEndPoint(url + LIBRARY_ENDPOINT + "/" + uid)
    except AppError, ae:
        raise ae


##############################################################
# getOwnerInfo()
#
#
def getUserInfo(uid):
    try:
        return executeEndPoint(url + USER_ENDPOINT + "/" + uid)
    except AppError, ae:
        raise ae


##############################################################
# getProjectScript()
# This function returns the UID of a specified dataset.
# Input:    project UID
# Returns:  The UID of the project
# Throws:   AppError bubbled up from executeEndPoint()
def getProjectScript(uid):
    try:
        return executeEndPoint(url + SCRIPT_ENDPOINT + "&projectId=" + uid)
    except AppError, ae:
        raise ae


##############################################################
# getProjectByID()
# This function retrieves the JSON object of a project specified by UID.
# Input:    uid of the project
# Returns:  The project JSON object.
# Throws:   AppError if the project was not found in Paxata or if the
# request status_code is not 200
def getProjectByID(uid):
    try:
        return executeEndPoint(url + PROJECT_ENDPOINT + "/" + uid)
    except AppError, ae:
        raise ae


##############################################################
# getProjectByName()
# This function retrieves the JSON object of a project specified by name.
# Input:    Name of the project.
# Returns:  The project JSON object. Stops on the first instance.
# Throws:   AppError if the project was not found in Paxata or if the
# request status_code is not 200
def getProjectByName(name):
    try:
        r = getProjectByID("")
        for obj in r:
            if obj.get('name') == name:
                return obj
        raise AppError('The project named: ' + name +
                       ' was not found in the library.', -1)
    except AppError, ae:
        raise ae


##############################################################
# Execute the request returns the response
# Input:    EndPoint to be executed
# Return:   Response content as a JSON object
# Throws:   AppError is the staus_code is not 200
def executeEndPoint(endpoint):
    r = requests.get(endpoint, auth=authTok)
    if r.status_code != 200:
        raise AppError("Error getting project script. Error is: " + r.reason + " (" + str(r.status_code) + ")",
                       r.status_code)
    return json.loads(r.content)

def makeCaption(step, caption, idx):
    html = '<table border="1" style="width:100%"><caption class="cpt">dscaption</caption>'
    cpt = 'caption'
    # Errors are not part of the script...too bad
    # if 'validationErrors' in step:
    #    print 'here'
    #    if len(step['$validationErrors']['Error']) > 0:
    #        cpt = 'captionErr'
    #        caption += " - "
    #        for err in step['$validationErrors']['Error']:
    #            caption += err['msg']
    html = re.sub("cpt", cpt, html)
    html = re.sub("dscaption", "Step " + str(idx) + ': ' + caption, html)
    return html



##############################################################
# Script main entry point
if __name__ == '__main__':
    main(sys.argv)
