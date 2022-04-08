from openforms.contrib.irma.client import IrmaClient, IrmaClientError

class IrmaClientManager:
    def __init__(self):
        self.client = IrmaClient(config)

    def getIrmaClient(self):
        return self.client
    
    def StartSession(self):
        self.client.start_session()

    def EndSession(self):
        self.client.end_session()
    