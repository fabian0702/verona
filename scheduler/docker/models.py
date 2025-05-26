from typing import Optional
from pydantic import BaseModel, RootModel

class PortConfig(BaseModel):
    published: Optional[int | str] = None
    target: int | str
    protocol: str

    def proxy_config(self) -> tuple[int, int, str]:
        """
        Returns the port configuration for the proxy.
        :return: A tuple containing the published and target ports.
        """
        return int(self.published or self.target), int(self.target), self.protocol
    
class PortConfigList(RootModel):
    root: list[PortConfig]

    def proxy_config(self) -> list[tuple[int, int, str]]:
        """
        Returns the port configurations for the proxy.
        :return: A list of tuples containing the published and target ports.
        """
        return [port.proxy_config() for port in self.root]
