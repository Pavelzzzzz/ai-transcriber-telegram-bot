class ServiceError(Exception):
    def __init__(self, message: str, service_name: str = None):
        self.message = message
        self.service_name = service_name
        super().__init__(self.message)


class KafkaProducerError(ServiceError):
    pass


class KafkaConsumerError(ServiceError):
    pass


class ProcessingError(ServiceError):
    pass


class ValidationError(ServiceError):
    pass
