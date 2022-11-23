#######################################################
#
# XMLCoTController.py
# Python implementation of the Class XMLCoTController
# Generated by Enterprise Architect
# Created on:      20-May-2020 1:07:38 PM
# Original author: Natha Paquette
#
#######################################################
from defusedxml import ElementTree as etree
import re
from digitalpy.core.object_factory import ObjectFactory

from FreeTAKServer.controllers.configuration.LoggingConstants import LoggingConstants
from FreeTAKServer.controllers.CreateLoggerController import CreateLoggerController
from FreeTAKServer.controllers.SpecificCoTControllers import *

from FreeTAKServer.model.SpecificCoT.SendPing import SendPing
from FreeTAKServer.model.SpecificCoT.SendTakPong import SendTakPong
from FreeTAKServer.model.SpecificCoT.SendUserUpdate import SendUserUpdate
from FreeTAKServer.model.SpecificCoT.SendDropPoint import SendDropPoint
from FreeTAKServer.model.SpecificCoT.SendOther import SendOther
from FreeTAKServer.model.SpecificCoT.SendGeoChat import SendGeoChat

from FreeTAKServer.model.FTSModel.Event import Event

logger = CreateLoggerController("XMLCoTController").getLogger()
loggingConstants = LoggingConstants()

TYPE_MAPPING_FORMAT = "MEMORY"


class XMLCoTController:
    def __init__(self, logger=logger):
        self.logger = logger

    def serialize_node(self, node) -> str:
        action_mapper = ObjectFactory.get_instance("syncactionmapper")
        request = ObjectFactory.get_instance("request")
        response = ObjectFactory.get_instance("response")
        request.set_value("node", node)
        request.set_action("NodeToXML")
        action_mapper.process_action(request, response)
        return response.get_value("message")

    def determineCoTGeneral(self, data, client_information_queue):

        # this will establish the CoTs general type
        if data.type == "RawConnectionInformation":
            # this handels the event of a connection CoT
            try:
                return ("clientConnected", data)

            except Exception as e:
                self.logger.error(
                    loggingConstants.XMLCOTCONTROLLERDETERMINECOTGENERALERRORA + str(e)
                )
        # this runs if it is infact regular data
        elif data.xmlString == b"" or data.xmlString == None:
            # this handeles a client dissconection CoT
            return ("clientDisconnected", data)
        else:
            # serialize the XML to an etree object
            event = etree.fromstring(data.xmlString)
            request = ObjectFactory.get_new_instance("request")
            request.set_action("XMLToDict")
            request.set_value("message", data.xmlString)

            actionmapper = ObjectFactory.get_instance("syncactionMapper")
            response = ObjectFactory.get_new_instance("response")
            actionmapper.process_action(request, response)

            # dictionary representation of the xml
            data_dict = response.get_value("dict")

            # this convert the machine readable type to a human readable type
            request = ObjectFactory.get_new_instance("request")
            request.set_format("pickled")
            request.set_action("ConvertMachineReadableToHumanReadable")
            request.set_context("MEMORY")
            request.set_value("machine_readable_type", data_dict["event"]["@type"])
            request.set_value("default", data_dict["event"]["@type"])

            # must get a new instance of the async action mapper for each request
            # to prevent run conditions and to prevent responses going to the wrong
            # callers
            actionmapper = ObjectFactory.get_instance("syncactionMapper")
            response = ObjectFactory.get_new_instance("response")
            actionmapper.process_action(request, response)

            # handle the case where the human readable type is not registered and there is no specific
            # component meant to handle the cot type
            if response.get_value("human_readable_type") == data_dict["event"]["@type"]:
                # return to call the legacy handler method
                return ("dataReceived", data)
            # handle the case where there is a specific component meant to handle the cot type
            else:
                # assign the human readable type to prevent the duplication of work
                data_dict["event"]["@type"] = response.get_value("human_readable_type")
                data.xmlString = response.get_value("message")
                data.data_dict = data_dict
                return ("component_handler", data)

    def convert_model_to_row(self, modelObject, rowObject):
        for attribName, attribValue in modelObject.__dict__.items():
            if hasattr(attribValue, "__dict__"):
                subTableRow = getattr(rowObject, attribName)
                subTableRowObject = self.convert_model_to_row(attribValue, subTableRow)
                setattr(rowObject, attribName, subTableRowObject)
            else:
                setattr(rowObject, attribName, attribValue)

    def determine_model_object_type(self, type_id):
        if type_id == "t-x-c-t":
            return Event.Ping, SendPing
        elif type_id == "t-x-c-t-r":
            return Event.takPong, SendTakPong
        elif type_id == "b-t-f":
            return Event.GeoChat, SendGeoChat
        elif re.match("^a-f-G-", type_id):
            return Event.UserUpdate, SendUserUpdate
        elif re.match("^a-.-.$", type_id):
            return Event.dropPoint, SendDropPoint
        else:
            return Event.Other, SendOther
        CoTTypes = {
            "t-x-c-t": Event.Ping,
            "t-x-c-t-r": Event.takPong,
            "b-t-f": Event.GeoChat,
        }

    def determineCoTType(self, RawCoT):
        # this function is to establish which specific controller apply to the CoT if any
        try:
            xml = RawCoT.xmlString
            if type(xml) != type(b""):
                xml = xml.encode()
            else:
                pass
            event = etree.fromstring(xml)
            detail = event.find("detail")
            CoTTypes = {
                "*": "SendOtherController",
                "emergency": "SendEmergencyController",
                "invalid": "SendInvalidCoTController",
                "health": "SendHealthCheckController",
                "ping": "SendPingController",
                "geochat": "SendGeoChatController",
                "point": "SendDropPointController",
                "userupdate": "SendUserUpdateController",
            }
            # TODO: the below if statement is probably unnecessary but this needs to be verified
            if RawCoT == b"" or RawCoT == None:
                RawCoT.disconnect = 1

            elif detail.find("emergency") != None:
                RawCoT.CoTType = CoTTypes["emergency"]
                emergency = detail.find("emergency")
                try:
                    if emergency.attrib["cancel"] == "true":
                        RawCoT.status = "off"
                except:
                    RawCoT.status = "on"

            elif str(event.attrib["type"]) == "t-x-c-t":
                RawCoT.CoTType = CoTTypes["ping"]
                return RawCoT

            elif str(event.attrib["type"]) == "b-t-f":
                RawCoT.CoTType = CoTTypes["geochat"]
                return RawCoT

            elif str(event.attrib["type"]) in [
                "a-f-G-U-C",
                "a-f-G-E-V-A",
                "a-f-G-U-C-I",
                "a-f-G-E-V-C",
                "a-f-G-U",
                "a-f-G-E-V-A",
            ]:
                RawCoT.CoTType = CoTTypes["userupdate"]
                return RawCoT

            elif (
                str(event.attrib["type"]) == "a-h-G"
                or str(event.attrib["type"]) == "a-n-G"
                or str(event.attrib["type"]) == "a-f-G"
                or str(event.attrib["type"]) == "a-u-G"
            ):
                RawCoT.CoTType = CoTTypes["point"]
                return RawCoT

            elif str(event.attrib["type"]) == "t-x-m-c":
                logger.debug("a txmc type xml has been received \n")
                RawCoT.CoTType = CoTTypes["*"]
                return RawCoT
            # TODO: this needs to be expanded for more use cases
            else:
                RawCoT.CoTType = CoTTypes["*"]

            return RawCoT
        except Exception as e:
            RawCoT.CoTType = "SendInvalidCoTController"
            return RawCoT

    def categorize_type(self, type):
        from FreeTAKServer.controllers.RestMessageControllers.SendEmergencyController import (
            SendEmergencyController,
        )
        from FreeTAKServer.controllers.SpecificCoTControllers.SendDropPointController import (
            SendDropPointController,
        )
        from FreeTAKServer.controllers.SpecificCoTControllers.SendGeoChatController import (
            SendGeoChatController,
        )
        from FreeTAKServer.controllers.SpecificCoTControllers.SendHealthCheckController import (
            SendHealthCheckController,
        )
        from FreeTAKServer.controllers.SpecificCoTControllers.SendInvalidCoTController import (
            SendInvalidCoTController,
        )
        from FreeTAKServer.controllers.SpecificCoTControllers.SendOtherController import (
            SendOtherController,
        )
        from FreeTAKServer.controllers.SpecificCoTControllers.SendPingController import (
            SendPingController,
        )
        from FreeTAKServer.controllers.SpecificCoTControllers.SendUserUpdateController import (
            SendUserUpdateController,
        )

        CoTTypes = {
            "*": SendOtherController,
            "emergency": SendEmergencyController,
            "invalid": SendInvalidCoTController,
            "health": SendHealthCheckController,
            "ping": SendPingController,
            "geochat": SendGeoChatController,
            "point": SendDropPointController,
            "userupdate": SendUserUpdateController,
        }
        if type == "t-x-c-t":
            return CoTTypes["ping"]

        elif type == "b-t-f":
            return CoTTypes["geochat"]

        elif type in [
            "a-f-G-U-C",
            "a-f-G-E-V-A",
            "a-f-G-U-C-I",
            "a-f-G-E-V-C",
            "a-f-G-U",
            "a-f-G-E-V-A",
        ]:
            return CoTTypes["userupdate"]

        elif type == "a-h-G" or type == "a-n-G" or type == "a-f-G" or type == "a-u-G":
            return CoTTypes["point"]

        elif type == "t-x-m-c":
            logger.debug("a txmc type xml has been received \n")
            return CoTTypes["*"]

            # TODO: this needs to be expanded for more use cases

        else:
            return CoTTypes["*"]

    def findCallsign(self):
        pass

    def findMarti(self):
        pass

    def findUID(self):
        pass

    def serialize_model_to_CoT(self, modelObject, tagName="event", level=0):
        from lxml.etree import Element  # pylint: disable=no-name-in-module

        xml = Element(tagName)
        for attribName, value in modelObject.__dict__.items():
            if hasattr(value, "__dict__"):
                tagElement = self.serialize_model_to_CoT(
                    value, attribName, level=level + 1
                )
                # TODO: modify so double underscores are handled differently
                try:
                    if attribName[0] == "_":
                        tagElement.tag = "_" + tagElement.tag
                        xml.append(tagElement)
                except:
                    pass
                else:
                    xml.append(tagElement)

            elif value == None:
                continue

            elif isinstance(value, list):
                for element in value:
                    tagElement = self.serialize_model_to_CoT(
                        element, attribName, level=level + 1
                    )
                    # TODO: modify so double underscores are handled differently
                    try:
                        if attribName[0] == "_":
                            tagElement.tag = "_" + tagElement.tag
                            xml.append(tagElement)
                    except:
                        pass
                    else:
                        xml.append(tagElement)

            # handles text data within tag
            elif attribName == "INTAG":
                xml.text = value

            else:
                # TODO: modify so double underscores are handled differently
                # handles instances in which attribute name begins with double underscore
                try:
                    if attribName[0] == "_":
                        xml.attrib["_" + attribName] = value
                except:
                    pass
                else:
                    xml.attrib[attribName] = str(value)

        if level == 0:
            return etree.tostring(xml)
        else:
            return xml

    """def serialize_CoT_to_model(self, model, xml):
        attributes = xml.attrib
        if xml.text != None:
            setter = getattr(model, 'setINTAG')
            setter(xml.text)
        else:
            pass

        for key, value in attributes.items():
            setter = getattr(model, 'set'+key)
            setter(value)

        for element in xml:
            submodel = getattr(model, 'get'+element.tag)
            submodel = submodel()
            if isinstance(submodel, list):
                for submodel_item in submodel:
                    out = self.serialize_CoT_to_model(submodel_item, element)
                    setter = getattr(model, 'set' + element.tag)
                    setter(out)
            else:
                out = self.serialize_CoT_to_model(submodel, element)
                setter = getattr(model, 'set'+element.tag)
                setter(out)

        return model"""
